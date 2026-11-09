"""Spike S7 — ¿ClickPy corrige días cerrados? Y evidencia para los umbrales de `validate`.

Uso:  uv run python docs/spikes/s7_clickpy_revisions_thresholds.py [baseline] [salida]
      baseline: Parquet de una captura anterior (por defecto build/spikes/s5/by_year, de S5).
      salida:   directorio de trabajo para la prueba de lectura (por defecto build/spikes/s7).

~30 consultas de solo lectura a ClickPy. Usa el adaptador del producto para volver a leer la
serie, así que corre en el entorno del proyecto, no con dependencias inline.
Respalda docs/spikes/s7-clickpy-revisiones-y-umbrales.md.
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import statistics as st
import sys
import time
from collections import defaultdict
from pathlib import Path

import duckdb
import httpx
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from ecopy.sources.clickpy import ClickPy
from ecopy.store import Store

ENDPOINT = "https://sql-clickhouse.clickhouse.com/"
PER_DAY = "pypi.pypi_downloads_per_day"
BY_PYTHON = "pypi.pypi_downloads_per_day_by_version_by_python"
RANGES = [("", "d"), ("d", "m"), ("m", "s"), ("s", None)]
START = dt.date(2016, 1, 22)


def query(client: httpx.Client, sql: str) -> list[list[str]]:
    response = client.post(
        ENDPOINT, params={"user": "play", "wait_end_of_query": 1}, content=f"{sql} FORMAT TSV"
    )
    response.raise_for_status()
    summary = json.loads(response.headers["X-ClickHouse-Summary"])
    if int(summary["read_rows"]) < int(summary["total_rows_to_read"]):
        raise SystemExit("lectura parcial")
    rows = [line.split("\t") for line in response.text.split("\n") if line]
    if len(rows) >= 1000:
        raise SystemExit("resultado posiblemente truncado")
    return rows


def read_baseline(path: Path) -> dict[tuple[str, dt.date], int]:
    rows = {}
    for file in path.rglob("*.parquet"):
        table = pq.ParquetFile(file).read(columns=["project", "date", "count"])
        for project, day, count in zip(
            table["project"].to_pylist(), table["date"].to_pylist(), table["count"].to_pylist()
        ):
            rows[project, day] = count
    return rows


def revisions(client: httpx.Client, baseline: dict, end: dt.date) -> None:
    projects = sorted({project for project, _ in baseline})
    batch = ClickPy(client).daily_downloads(projects, START, end)
    now = {(row.project, row.date): row.downloads for row in batch.rows}
    changed = {key: (value, now[key]) for key, value in baseline.items() if now.get(key, value) != value}
    gone = [key for key in baseline if key not in now]
    print(f"baseline {len(baseline):,} filas · cambiaron {len(changed):,} · desaparecieron {len(gone):,}")
    by_day = defaultdict(int)
    for (_, day), _values in changed.items():
        by_day[day] += 1
    print("días con cambios:", dict(sorted(by_day.items())))


def daily_totals(client: httpx.Client) -> dict[dt.date, int]:
    [[packed]] = query(
        client,
        "SELECT arrayStringConcat(arrayMap(x -> concat(toString(x.1), ':', toString(x.2)), "
        f"arraySort(groupArray((date, n)))), ',') FROM (SELECT date, sum(count) n FROM {PER_DAY} GROUP BY date)",
    )
    return {dt.date.fromisoformat(i.split(":")[0]): int(i.split(":")[1]) for i in packed.split(",")}


def thresholds(days: dict[dt.date, int]) -> None:
    ratios = []
    for day, value in sorted(days.items()):
        previous = [days.get(day - dt.timedelta(days=7 * k)) for k in range(1, 5)]
        if all(previous):
            ratios.append((day, value / st.median(previous)))
    since_2020 = sorted(r for d, r in ratios if d >= dt.date(2020, 1, 1))
    print(f"desde 2020: {len(since_2020)} días, mínimo {since_2020[0]:.3f}, máximo {since_2020[-1]:.3f}")
    print("bajo 0,5 antes de 2020:", [(str(d), round(r, 2)) for d, r in ratios if r < 0.5 and d.year < 2020])
    print("bajo 0,7 desde 2026:", [(str(d), round(r, 2)) for d, r in ratios if r < 0.7 and d.year >= 2026])


def versions_vs_total(client: httpx.Client) -> None:
    by_month: dict[str, int] = defaultdict(int)
    for low, high in RANGES:
        bounds = f"project >= '{low}'" + (f" AND project < '{high}'" if high else "")
        for month, total in query(
            client, f"SELECT toStartOfMonth(date), sum(count) FROM {BY_PYTHON} WHERE {bounds} GROUP BY 1"
        ):
            by_month[month] += int(total)
    totals = dict(query(client, f"SELECT toStartOfMonth(date), sum(count) FROM {PER_DAY} GROUP BY 1"))
    different = {m: v - int(totals.get(m, 0)) for m, v in sorted(by_month.items()) if v != int(totals.get(m, 0))}
    print(f"versiones contra total: difieren {len(different)} de {len(by_month)} meses: {different}")


def package_gaps(baseline: dict, days: dict[dt.date, int]) -> None:
    by_project = defaultdict(set)
    for project, day in baseline:
        by_project[project].add(day)
    missing = defaultdict(int)
    for project, seen in by_project.items():
        for offset in range((max(seen) - min(seen)).days + 1):
            day = min(seen) + dt.timedelta(days=offset)
            missing[project] += day in days and day not in seen
    affected = {p: n for p, n in missing.items() if n}
    print(f"paquetes con días propios sin filas: {len(affected)} de {len(by_project)}, {sum(affected.values())} días")


def read_cost(baseline_dir: Path, out: Path) -> None:
    shutil.rmtree(out, ignore_errors=True)
    year = out / "raw/clickpy/downloads_daily/year=2026"
    year.mkdir(parents=True)
    tables = [pq.read_table(f) for f in baseline_dir.rglob("*.parquet")]
    table = pa.concat_tables(t.select(["date", "project", "count", "source", "acquisition", "captured_at", "ingestion_run_id"]) for t in tables)
    table = table.rename_columns(["date", "project", "downloads", "source", "acquisition", "captured_at", "ingestion_run_id"])
    pq.write_table(table, year / "backfill.parquet", compression="zstd")
    last = table.filter(pc.equal(table["date"], pa.scalar(dt.date(2026, 11, 6), pa.date32())))
    for i in range(3650):
        day = dt.date(2026, 11, 7) + dt.timedelta(days=i)
        pq.write_table(last.set_column(0, "date", pa.array([day] * len(last), pa.date32())), year / f"r{i:05d}.parquet", compression="zstd")
    projects = sorted(set(last["project"].to_pylist()))
    start = time.monotonic()
    series = Store(out).daily_downloads(projects)
    print(f"Store.daily_downloads: {time.monotonic() - start:.2f} s, {sum(map(len, series.values())):,} filas")
    start = time.monotonic()
    duckdb.connect().execute(f"SELECT project, max(date) FROM read_parquet('{year}/*.parquet') GROUP BY 1").fetchall()
    print(f"último día por paquete: {time.monotonic() - start:.2f} s")


def main() -> None:
    baseline_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "build/spikes/s5/by_year")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "build/spikes/s7")
    baseline = read_baseline(baseline_dir)
    end = dt.datetime.now(dt.UTC).date() - dt.timedelta(days=1)
    with httpx.Client(timeout=180) as client:
        revisions(client, baseline, end)
        days = daily_totals(client)
        thresholds(days)
        versions_vs_total(client)
    package_gaps(baseline, days)
    read_cost(baseline_dir, out)


if __name__ == "__main__":
    main()
