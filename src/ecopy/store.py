"""Store append-only de Parquet: nunca reescribe y lee resolviendo correcciones."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from ecopy.models import (
    AppendResult,
    Batch,
    DailySeries,
    DatasetCounts,
    DownloadBatch,
    Problem,
    PypiTotalsBatch,
    PythonMinorBatch,
    Run,
    RunReport,
    StarsReport,
    StarTotalsBatch,
    StarWeeksBatch,
    YearView,
)


class ImmutabilityError(Exception):
    """Se intentó escribir sobre un archivo existente: el store nunca reescribe."""


@dataclass(frozen=True)
class _Column:
    name: str
    type: pa.DataType
    read: Callable


@dataclass(frozen=True)
class _Dataset:
    name: str
    key: tuple[_Column, ...]
    partition: Callable[[object], int]
    """Año del registro."""
    value: str = "downloads"

    def key_of(self, row: object) -> tuple:
        return tuple(column.read(row) for column in self.key)

    @property
    def key_names(self) -> str:
        return ", ".join(column.name for column in self.key)


def _attr(name: str) -> Callable:
    return lambda row: getattr(row, name)


_DATASETS: dict[type, _Dataset] = {
    DownloadBatch: _Dataset(
        "downloads_daily",
        (
            _Column("project", pa.string(), _attr("project")),
            _Column("date", pa.date32(), _attr("date")),
        ),
        lambda row: row.date.year,
    ),
    PypiTotalsBatch: _Dataset(
        "pypi_total_daily",
        (_Column("date", pa.date32(), _attr("date")),),
        lambda row: row.date.year,
    ),
    PythonMinorBatch: _Dataset(
        "python_minor_monthly",
        (
            _Column("month", pa.date32(), _attr("month")),
            _Column("python_minor", pa.string(), _attr("python_minor")),
        ),
        lambda row: row.month.year,
    ),
    StarWeeksBatch: _Dataset(
        "star_weeks",
        (
            _Column("repo", pa.string(), _attr("repo")),
            _Column("week", pa.date32(), _attr("week")),
        ),
        lambda row: row.week.year,
        "stars",
    ),
    StarTotalsBatch: _Dataset(
        "star_totals",
        (
            _Column("repo", pa.string(), _attr("repo")),
            _Column("date", pa.date32(), _attr("date")),
        ),
        lambda row: row.date.year,
        "stars",
    ),
}


def _write_new(table: pa.Table, path: Path) -> None:
    """Escritura atómica que no puede pisar: `link` falla si el destino ya existe."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        pq.write_table(table, temporary, compression="zstd", compression_level=9)
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise ImmutabilityError(f"ya existe: {path}") from error
    finally:
        temporary.unlink(missing_ok=True)


def _write_text_new(path: Path, text: str) -> None:
    """Escritura atómica de texto que no puede pisar un archivo existente."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise ImmutabilityError(f"ya existe: {path}") from error
    finally:
        temporary.unlink(missing_ok=True)


def _table(dataset: _Dataset, rows: Sequence, source: str, run: Run) -> pa.Table:
    columns = {c.name: pa.array([c.read(r) for r in rows], c.type) for c in dataset.key}
    size = len(rows)
    return pa.table(
        {
            **columns,
            dataset.value: pa.array([getattr(r, dataset.value) for r in rows], pa.int64()),
            "source": pa.array([source] * size, pa.string()),
            "acquisition": pa.array([run.acquisition] * size, pa.string()),
            "captured_at": pa.array([run.captured_at] * size, pa.timestamp("us", tz="UTC")),
            "ingestion_run_id": pa.array([run.id] * size, pa.string()),
        }
    )


def _report_from(data: dict) -> RunReport:
    return RunReport(
        id=data["id"],
        captured_at=datetime.fromisoformat(data["captured_at"]),
        status=data["status"],
        problems=tuple(Problem(**problem) for problem in data["problems"]),
        datasets={name: DatasetCounts(**counts) for name, counts in data["datasets"].items()},
        last_day=date.fromisoformat(data["last_day"]) if data["last_day"] else None,
    )


class Store:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def append(self, batch: Batch, run: Run) -> AppendResult:
        """Escribe solo las filas nuevas o distintas de la versión vigente, un archivo por año."""
        dataset = _DATASETS[type(batch)]
        if list(self._root.glob(f"raw/*/{dataset.name}/year=*/{run.id}.parquet")):
            raise ImmutabilityError(f"la corrida {run.id} ya escribió {dataset.name}")
        current = self._current(dataset, {dataset.partition(r) for r in batch.rows})
        by_year: dict[int, list] = defaultdict(list)
        new_rows = revised_rows = 0
        for row in sorted(batch.rows, key=dataset.key_of):
            known = current.get(dataset.key_of(row))
            if known == getattr(row, dataset.value):
                continue
            new_rows += known is None
            revised_rows += known is not None
            by_year[dataset.partition(row)].append(row)
        directory = self._root / "raw" / batch.source / dataset.name
        paths = []
        for year, rows in sorted(by_year.items()):
            path = directory / f"year={year}" / f"{run.id}.parquet"
            _write_new(_table(dataset, rows, batch.source, run), path)
            paths.append(path)
        return AppendResult(paths, new_rows, revised_rows)

    def _files(self, dataset: _Dataset, years: set[int] | None = None) -> list[str]:
        found = self._root.glob(f"raw/*/{dataset.name}/year=*/*.parquet")
        return sorted(
            str(f) for f in found if years is None or int(f.parent.name.split("=")[1]) in years
        )

    def _latest(
        self, dataset: _Dataset, files: list[str], where: str = "", params: Sequence = ()
    ) -> list[tuple]:
        """Filas vigentes: por cada clave gana la captura más reciente."""
        if not files:
            return []
        keys = dataset.key_names
        return (
            duckdb.connect(":memory:")
            .execute(
                f"""SELECT {keys}, {dataset.value} FROM read_parquet(?) {where}
                    QUALIFY row_number() OVER (
                        PARTITION BY {keys} ORDER BY captured_at DESC, ingestion_run_id DESC
                    ) = 1
                    ORDER BY {keys}""",
                [files, *params],
            )
            .fetchall()
        )

    def _current(self, dataset: _Dataset, years: set[int]) -> dict[tuple, int]:
        rows = self._latest(dataset, self._files(dataset, years))
        return {tuple(row[:-1]): row[-1] for row in rows}

    def daily_downloads(self, projects: Sequence[str]) -> dict[str, DailySeries]:
        dataset = _DATASETS[DownloadBatch]
        rows = self._latest(
            dataset, self._files(dataset), "WHERE list_contains(?, project)", [list(projects)]
        )
        series: dict[str, dict] = {}
        for project, day, downloads in rows:
            series.setdefault(project, {})[day] = downloads
        return series

    def pypi_daily_totals(self) -> DailySeries:
        dataset = _DATASETS[PypiTotalsBatch]
        return dict(self._latest(dataset, self._files(dataset)))

    def python_minor_monthly(self) -> dict[date, dict[str, int]]:
        dataset = _DATASETS[PythonMinorBatch]
        months: dict[date, dict[str, int]] = {}
        for month, minor, downloads in self._latest(dataset, self._files(dataset)):
            months.setdefault(month, {})[minor] = downloads
        return months

    def _by_repo(self, kind: type, repos: Sequence[str]) -> dict[str, dict[date, int]]:
        dataset = _DATASETS[kind]
        rows = self._latest(
            dataset, self._files(dataset), "WHERE list_contains(?, repo)", [list(repos)]
        )
        found: dict[str, dict[date, int]] = {}
        for repo, day, stars in rows:
            found.setdefault(repo, {})[day] = stars
        return found

    def star_weeks(self, repos: Sequence[str]) -> dict[str, dict[date, int]]:
        """Estrellas netas por semana de cada repo."""
        return self._by_repo(StarWeeksBatch, repos)

    def star_totals(self, repos: Sequence[str]) -> dict[str, dict[date, int]]:
        """`stargazers_count` por día de corrida de cada repo."""
        return self._by_repo(StarTotalsBatch, repos)

    def backfilled_repos(self) -> set[str]:
        """Repos cuya historia completa ya se guardó."""
        files = self._files(_DATASETS[StarWeeksBatch])
        if not files:
            return set()
        rows = duckdb.connect(":memory:").execute(
            "SELECT DISTINCT repo FROM read_parquet(?) WHERE acquisition = 'backfill'", [files]
        )
        return {repo for (repo,) in rows.fetchall()}

    def record_stars_run(self, report: StarsReport) -> None:
        """Va en su propio directorio: `site_status` solo mira las corridas de descargas."""
        text = json.dumps(asdict(report), default=str, indent=1) + "\n"
        _write_text_new(self._root / "runs" / "stars" / f"{report.id}.json", text)

    def record_run(self, report: RunReport) -> None:
        """Guarda el registro de una ejecución; igual que los datos, no se reescribe."""
        text = json.dumps(asdict(report), default=str, indent=1) + "\n"
        _write_text_new(self._root / "runs" / f"{report.id}.json", text)

    def freeze_year(self, view: YearView) -> Path:
        """Fija la vista de un año cerrado. Una metodología nueva es un archivo nuevo."""
        name = f"year={view.year}/methodology={view.methodology_version}.json"
        path = self._root / "frozen" / name
        _write_text_new(path, view.model_dump_json(indent=1) + "\n")
        return path

    def frozen_year(self, year: int) -> YearView | None:
        """La vista congelada de un año, en su metodología más alta; None si no hay."""
        files = (self._root / "frozen" / f"year={year}").glob("methodology=*.json")
        newest = max(files, key=lambda f: int(f.stem.split("=")[1]), default=None)
        if newest is None:
            return None
        return YearView.model_validate_json(newest.read_text(encoding="utf-8"))

    def runs(self) -> tuple[RunReport, ...]:
        """Registros de las ejecuciones, de la más vieja a la más nueva."""
        return tuple(
            _report_from(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted((self._root / "runs").glob("*.json"))
        )

    def last_days(self) -> dict[str, date]:
        """Último día con datos de cada paquete, sin cargar las series."""
        files = self._files(_DATASETS[DownloadBatch])
        if not files:
            return {}
        rows = duckdb.connect(":memory:").execute(
            "SELECT project, max(date) FROM read_parquet(?) GROUP BY project", [files]
        )
        return dict(rows.fetchall())
