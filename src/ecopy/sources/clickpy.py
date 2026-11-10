"""Adaptador de ClickPy: descargas diarias completas y verificadas, o una excepción."""

from __future__ import annotations

import json
import time
from collections import defaultdict
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import date

import httpx

from ecopy.models import (
    DailyDownload,
    DailyTotal,
    DownloadBatch,
    PypiTotalsBatch,
    PythonMinorBatch,
    PythonMinorMonth,
)

ENDPOINT = "https://sql-clickhouse.clickhouse.com/"
PER_DAY = "pypi.pypi_downloads_per_day"
BY_PYTHON = "pypi.pypi_downloads_per_day_by_version_by_python"

# Límites del usuario `play`: al pasarlos, ClickPy corta la respuesta SIN error HTTP.
MAX_RESULT_ROWS = 1000
MAX_RESULT_BYTES = 10_000_000
ATTEMPTS = 3
# Lote que deja la serie diaria completa (~5 MB, S5) bien por debajo de MAX_RESULT_BYTES.
BATCH_SIZE = 50
# La tabla por versión (~10.600 M de filas) pasa el límite de lectura: su clave empieza por
# `project`, así que se lee por rangos de nombre; filtrar por fecha no reduce lo leído (S2).
PROJECT_RANGES = (("", "d"), ("d", "m"), ("m", "s"), ("s", None))
KNOWN_BATCH_SIZE = 500
TOP_YEARS_PER_QUERY = 5


class SourceError(Exception):
    """Error base de las fuentes de datos."""


class TruncatedResult(SourceError):
    """ClickPy devolvió un resultado parcial (lo hace sin error HTTP al pasar sus límites)."""


class ChecksumMismatch(SourceError):
    """La descarga no cuadra con las sumas de control calculadas en el servidor."""


class SourceUnavailable(SourceError):
    """La fuente no respondió tras los reintentos."""


class MalformedResponse(SourceError):
    """La respuesta no tiene la forma esperada (encabezados, campos o valores)."""


@contextmanager
def _parsing(tag: str) -> Iterator[None]:
    """Un cuerpo con otra forma (campos de menos, fecha o número inválidos) es un SourceError."""
    try:
        yield
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise MalformedResponse(f"{tag}: respuesta con forma inesperada: {error!r}") from error


def _in_list(projects: Sequence[str]) -> str:
    return ", ".join("'" + p.replace("\\", "\\\\").replace("'", "\\'") + "'" for p in projects)


class ClickPy:
    def __init__(
        self, client: httpx.Client, *, sleep: Callable[[float], None] = time.sleep
    ) -> None:
        self._client = client
        self._sleep = sleep

    def daily_downloads(self, projects: Sequence[str], start: date, end: date) -> DownloadBatch:
        """Registros por (paquete, día) del rango, completos y verificados.

        Ordenados por paquete y fecha. Un paquete sin descargas en el rango no aparece.
        Lanza SourceError (o una subclase): nunca devuelve un resultado parcial.
        """
        if start > end:
            raise ValueError(f"rango invertido: {start} > {end}")
        rows: list[DailyDownload] = []
        with _parsing("daily"):
            for i in range(0, len(projects), BATCH_SIZE):
                rows += self._fetch_batch(projects[i : i + BATCH_SIZE], start, end)
        rows.sort(key=lambda r: (r.project, r.date))
        return DownloadBatch(source="clickpy", rows=tuple(rows))

    def pypi_daily_totals(self, start: date, end: date) -> PypiTotalsBatch:
        """Descargas de todo PyPI por día, verificadas contra la suma de control del servidor."""
        if start > end:
            raise ValueError(f"rango invertido: {start} > {end}")
        with _parsing("totals"):
            where = f"date BETWEEN '{start}' AND '{end}'"
            rows = self._query(
                "totals",
                f"""SELECT arrayStringConcat(
                           arrayMap(x -> concat(toString(x.1), ':', toString(x.2)),
                                    arraySort(groupArray((date, n)))), ',')
                    FROM (SELECT date, sum(count) AS n FROM {PER_DAY}
                          WHERE {where} GROUP BY date)""",
            )
            packed = rows[0][0] if rows else ""
            totals = [
                DailyTotal(date.fromisoformat(day), int(count))
                for day, count in (item.split(":") for item in packed.split(",") if item)
            ]
            [[days, total]] = self._query(
                "totals_checksums",
                f"SELECT uniqExact(date), sum(count) FROM {PER_DAY} WHERE {where}",
            )
            got = (len(totals), sum(row.downloads for row in totals))
            if got != (int(days), int(total)):
                raise ChecksumMismatch(f"totales: descarga {got} != servidor {(days, total)}")
        return PypiTotalsBatch(source="clickpy", rows=tuple(totals))

    def python_minor_monthly(self, before: date) -> PythonMinorBatch:
        """Descargas de todo PyPI por mes y versión, de los meses anteriores a `before`.

        `python_minor` sale crudo, con la basura que traiga la fuente: filtrar es de `metrics`.
        """
        if before.day != 1:
            raise ValueError(f"`before` debe ser el primer día de un mes: {before}")
        totals: dict[tuple[date, str], int] = defaultdict(int)
        with _parsing("python"):
            for low, high in PROJECT_RANGES:
                bounds = f"project >= '{low}'" + (f" AND project < '{high}'" if high else "")
                where = f"{bounds} AND date < '{before}'"
                # `python_minor` trae comas y barras: separadores de control y split("\n").
                rows = self._query(
                    "python",
                    f"""SELECT arrayStringConcat(
                               arrayMap(x -> concat(toString(x.1), char(31), x.2, char(31),
                                                    toString(x.3)),
                                        groupArray((m, python_minor, n))), char(30))
                        FROM (SELECT toStartOfMonth(date) AS m, python_minor, sum(count) AS n
                              FROM {BY_PYTHON} WHERE {where} GROUP BY m, python_minor)""",
                )
                packed = rows[0][0] if rows else ""
                items = [item.split("\x1f") for item in packed.split("\x1e") if item]
                for month, minor, downloads in items:
                    totals[date.fromisoformat(month), minor] += int(downloads)
                [[expected]] = self._query(
                    "python_checksums", f"SELECT sum(count) FROM {BY_PYTHON} WHERE {where}"
                )
                got = sum(int(downloads) for _, _, downloads in items)
                if got != int(expected):
                    raise ChecksumMismatch(f"versiones {bounds}: {got} != servidor {expected}")
        rows = tuple(PythonMinorMonth(m, minor, n) for (m, minor), n in sorted(totals.items()))
        return PythonMinorBatch(source="clickpy", rows=rows)

    def top_projects(self, years: Sequence[int], n: int = 100) -> Mapping[int, tuple[str, ...]]:
        """Los `n` paquetes más descargados de cada año, en orden de ranking."""
        ranking: dict[int, list[str]] = defaultdict(list)
        with _parsing("top"):
            for i in range(0, len(years), TOP_YEARS_PER_QUERY):
                chunk = ", ".join(str(year) for year in years[i : i + TOP_YEARS_PER_QUERY])
                for year, project, _ in self._query(
                    "top",
                    f"""SELECT toYear(date) AS y, project, sum(count) AS s FROM {PER_DAY}
                        WHERE toYear(date) IN ({chunk})
                        GROUP BY y, project ORDER BY y, s DESC LIMIT {n} BY y""",
                ):
                    ranking[int(year)].append(project)
        short = {year: len(ranking[year]) for year in years if len(ranking[year]) != n}
        if short:
            raise ChecksumMismatch(f"top {n} incompleto: {short}")
        return {year: tuple(ranking[year]) for year in years}

    def known_projects(self, projects: Sequence[str]) -> set[str]:
        """Los paquetes de la lista que tienen algún dato en la fuente."""
        known: set[str] = set()
        for i in range(0, len(projects), KNOWN_BATCH_SIZE):
            batch = projects[i : i + KNOWN_BATCH_SIZE]
            rows = self._query(
                "known",
                f"SELECT project FROM {PER_DAY} WHERE project IN ({_in_list(batch)}) "
                "GROUP BY project",
            )
            known |= {row[0] for row in rows}
        return known

    def _fetch_batch(self, projects: Sequence[str], start: date, end: date) -> list[DailyDownload]:
        # La tabla es un SummingMergeTree: un (paquete, día) puede estar en varias filas sin
        # fusionar, así que siempre se agrupa y se suma. Una fila por paquete con la serie
        # empaquetada esquiva el límite de 1.000 filas de resultado.
        where = f"project IN ({_in_list(projects)}) AND date BETWEEN '{start}' AND '{end}'"
        sql = f"""
            SELECT project,
                   arrayStringConcat(
                       arrayMap(x -> concat(toString(x.1), ':', toString(x.2)),
                                arraySort(groupArray((date, n)))), ',')
            FROM (SELECT project, date, sum(count) AS n FROM {PER_DAY}
                  WHERE {where}
                  GROUP BY project, date)
            GROUP BY project"""
        rows = [
            DailyDownload(project, date.fromisoformat(day), int(count))
            for project, packed in self._query("daily", sql)
            for day, count in (item.split(":") for item in packed.split(","))
        ]
        self._verify(rows, where)
        return rows

    def _verify(self, rows: Sequence[DailyDownload], where: str) -> None:
        """Cuadra la descarga contra (días, suma) por paquete, calculados en el servidor."""
        expected = {
            project: (int(days), int(total))
            for project, days, total in self._query(
                "checksums",
                f"SELECT project, uniqExact(date), sum(count) FROM {PER_DAY} "
                f"WHERE {where} GROUP BY project",
            )
        }
        got: dict[str, tuple[int, int]] = {}
        for row in rows:
            days, total = got.get(row.project, (0, 0))
            got[row.project] = (days + 1, total + row.downloads)
        if got != expected:
            raise ChecksumMismatch(f"descarga {got} != servidor {expected}")

    def _post(self, tag: str, sql: str) -> httpx.Response:
        """POST con reintentos ante fallas transitorias; un rechazo (4xx) no se reintenta."""
        failure = ""
        for attempt in range(ATTEMPTS):
            if attempt:
                self._sleep(2**attempt)
            try:
                # wait_end_of_query=1: el resumen sale al final y el status HTTP es confiable.
                response = self._client.post(
                    ENDPOINT,
                    params={"user": "play", "wait_end_of_query": 1},
                    content=f"/* ecopy:{tag} */ {sql} FORMAT TSV",
                )
            except httpx.TransportError as error:
                failure = repr(error)
                continue
            if response.status_code >= 500:
                failure = f"HTTP {response.status_code}"
                continue
            if response.is_error:
                raise SourceError(f"{tag}: HTTP {response.status_code}: {response.text[:500]}")
            return response
        raise SourceUnavailable(f"{tag}: {failure} tras {ATTEMPTS} intentos")

    def _query(self, tag: str, sql: str) -> list[list[str]]:
        response = self._post(tag, sql)
        try:
            summary = json.loads(response.headers["X-ClickHouse-Summary"])
            read, total = int(summary["read_rows"]), int(summary["total_rows_to_read"])
            result_bytes = int(summary["result_bytes"])
        except (KeyError, TypeError, ValueError) as error:
            raise MalformedResponse(f"{tag}: resumen inválido: {error!r}") from error
        if read < total:
            raise TruncatedResult(f"{tag}: se leyeron {read:,} de {total:,} filas")
        if result_bytes >= MAX_RESULT_BYTES * 0.9:
            raise TruncatedResult(f"{tag}: {result_bytes} bytes, cerca del límite")
        # split("\n") y no splitlines(): este último también corta en \x1c-\x1e.
        rows = [line.split("\t") for line in response.text.split("\n") if line]
        if len(rows) >= MAX_RESULT_ROWS:
            raise TruncatedResult(f"{tag}: {len(rows)} filas, posible corte en el límite")
        return rows
