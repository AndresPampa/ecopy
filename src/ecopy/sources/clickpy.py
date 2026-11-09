"""Adaptador de ClickPy: descargas diarias completas y verificadas, o una excepción."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from datetime import date

import httpx

from ecopy.models import DailyDownload, DownloadBatch

ENDPOINT = "https://sql-clickhouse.clickhouse.com/"
PER_DAY = "pypi.pypi_downloads_per_day"

# Límites del usuario `play`: al pasarlos, ClickPy corta la respuesta SIN error HTTP.
MAX_RESULT_ROWS = 1000
MAX_RESULT_BYTES = 10_000_000
ATTEMPTS = 3
# Lote que deja la serie diaria completa (~5 MB, S5) bien por debajo de MAX_RESULT_BYTES.
BATCH_SIZE = 50


class SourceError(Exception):
    """Error base de las fuentes de datos."""


class TruncatedResult(SourceError):
    """ClickPy devolvió un resultado parcial (lo hace sin error HTTP al pasar sus límites)."""


class ChecksumMismatch(SourceError):
    """La descarga no cuadra con las sumas de control calculadas en el servidor."""


class SourceUnavailable(SourceError):
    """La fuente no respondió tras los reintentos."""


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
        for i in range(0, len(projects), BATCH_SIZE):
            rows += self._fetch_batch(projects[i : i + BATCH_SIZE], start, end)
        rows.sort(key=lambda r: (r.project, r.date))
        return DownloadBatch(source="clickpy", rows=tuple(rows))

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
        summary = json.loads(response.headers["X-ClickHouse-Summary"])
        read, total = int(summary["read_rows"]), int(summary["total_rows_to_read"])
        if read < total:
            raise TruncatedResult(f"{tag}: se leyeron {read:,} de {total:,} filas")
        if int(summary["result_bytes"]) >= MAX_RESULT_BYTES * 0.9:
            raise TruncatedResult(f"{tag}: {summary['result_bytes']} bytes, cerca del límite")
        # split("\n") y no splitlines(): este último también corta en \x1c-\x1e.
        rows = [line.split("\t") for line in response.text.split("\n") if line]
        if len(rows) >= MAX_RESULT_ROWS:
            raise TruncatedResult(f"{tag}: {len(rows)} filas, posible corte en el límite")
        return rows
