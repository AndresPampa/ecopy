"""Store append-only de Parquet: nunca reescribe; lee resolviendo correcciones."""

from __future__ import annotations

import os
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from ecopy.models import DailyDownload, DailySeries, DownloadBatch, Run

DATASET = "downloads_daily"


class ImmutabilityError(Exception):
    """Se intentó escribir sobre un archivo existente: el store nunca reescribe."""


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


class Store:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def append(self, batch: DownloadBatch, run: Run) -> list[Path]:
        by_year: dict[int, list[DailyDownload]] = defaultdict(list)
        for row in sorted(batch.rows, key=lambda r: (r.project, r.date)):
            by_year[row.date.year].append(row)
        targets = {
            year: self._dataset(batch.source) / f"year={year}" / f"{run.id}.parquet"
            for year in sorted(by_year)
        }
        # Se revisa todo antes de escribir: una corrida rechazada no deja archivos sueltos.
        for path in targets.values():
            if path.exists():
                raise ImmutabilityError(f"ya existe: {path}")
        for year, path in targets.items():
            rows = by_year[year]
            table = pa.table(
                {
                    "project": pa.array([r.project for r in rows], pa.string()),
                    "date": pa.array([r.date for r in rows], pa.date32()),
                    "downloads": pa.array([r.downloads for r in rows], pa.int64()),
                    "source": pa.array([batch.source] * len(rows), pa.string()),
                    "acquisition": pa.array([run.acquisition] * len(rows), pa.string()),
                    "captured_at": pa.array(
                        [run.captured_at] * len(rows), pa.timestamp("us", tz="UTC")
                    ),
                    "ingestion_run_id": pa.array([run.id] * len(rows), pa.string()),
                }
            )
            _write_new(table, path)
        return list(targets.values())

    def _dataset(self, source: str) -> Path:
        return self._root / "raw" / source / DATASET

    def daily_downloads(self, projects: Sequence[str]) -> dict[str, DailySeries]:
        files = [str(f) for f in sorted(self._root.glob(f"raw/*/{DATASET}/year=*/*.parquet"))]
        if not files:
            return {}
        rows = duckdb.connect(":memory:").execute(
            """SELECT project, date, downloads FROM read_parquet(?)
               WHERE list_contains(?, project)
               QUALIFY row_number() OVER (
                   PARTITION BY project, date ORDER BY captured_at DESC, ingestion_run_id DESC
               ) = 1
               ORDER BY project, date""",
            [files, list(projects)],
        )
        series: dict[str, dict] = {}
        for project, day, downloads in rows.fetchall():
            series.setdefault(project, {})[day] = downloads
        return series
