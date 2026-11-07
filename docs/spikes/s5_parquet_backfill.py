# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "pyarrow>=18"]
# ///
"""Spike S5 — Tamaño real del Parquet y costo del backfill desde ClickPy.

Uso:  uv run docs/spikes/s5_parquet_backfill.py [directorio_salida]   (por defecto build/spikes/s5)

1. Arma un catálogo de ~500 paquetes como el del PRD: unión del top 100 de cada año desde 2017,
   completada hasta 500 con el ranking de 2025 (sustituto de la lista curada; sesgo hacia
   paquetes con historia larga → cota superior del tamaño).
2. Mide el costo del backfill con los límites del usuario `play` (1.000 filas y 10 MB de
   resultado, 10.000 M de filas leídas, 60 s por consulta): una fila por (paquete, día) frente a
   una fila por paquete con la serie empaquetada en un array.
3. Descarga la serie DIARIA y la MENSUAL de los paquetes del catálogo desde 2016-01-22, verifica
   cada lote contra sumas de control calculadas en el servidor y escribe Parquet (zstd) con las
   columnas de procedencia del PRD, en varias disposiciones de archivos.
4. Cuenta las filas que ocuparía el desglose mensual por versión de Python por paquete.
5. Imprime tamaños, costo y la proyección contra los límites de GitHub.

Los Parquet quedan en el directorio de salida (no se versiona). No guarda credenciales ni
identidades de usuarios.
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx
import pyarrow as pa
import pyarrow.parquet as pq

ENDPOINT = "https://sql-clickhouse.clickhouse.com/"
PER_DAY = "pypi.pypi_downloads_per_day"  # clave (project, date)
PER_MONTH = "pypi.pypi_downloads_per_month"  # clave (month, project)
BY_PY = "pypi.pypi_downloads_per_day_by_version_by_python"  # clave (project, version, date, python_minor)
START = "2016-01-22"
CATALOG_SIZE = 500
BATCH = 50  # paquetes por consulta en modo array (≈ 6,5 MB de resultado diario; límite 10 MB)

# Límites del usuario `play` (system.settings): con `*_overflow_mode=break` la respuesta llega
# TRUNCADA y sin error. Toda consulta verifica el resumen y falla ante un resultado parcial.
# `wait_end_of_query=1` hace que el resumen se emita al final: sin él, el encabezado sale con el
# primer bloque y `result_rows`/`result_bytes` llegan en 0. Además, cada descarga se cuadra contra
# sumas de control calculadas en el servidor (la defensa que no depende del resumen).
MAX_RESULT_ROWS = 1000
MAX_RESULT_BYTES = 10_000_000

STATS = {"queries": 0, "read_rows": 0, "result_bytes": 0, "wire_bytes": 0, "server_s": 0.0}


def query(client: httpx.Client, sql: str) -> list[list[str]]:
    resp = client.post(ENDPOINT, params={"user": "play", "wait_end_of_query": 1}, content=f"{sql} FORMAT TSV")
    if resp.is_error:
        raise SystemExit(f"ClickHouse {resp.status_code}: {resp.text[:500]}")
    s = json.loads(resp.headers["X-ClickHouse-Summary"])
    read, total = int(s["read_rows"]), int(s["total_rows_to_read"])
    rbytes = int(s.get("result_bytes", 0))
    # split("\n") y no splitlines(): este último corta también en \x1c–\x1e.
    rows = [line.split("\t") for line in resp.text.split("\n") if line]
    if read < total:
        raise SystemExit(f"Lectura parcial ({read:,} de {total:,} filas): partir la consulta.")
    if len(rows) >= MAX_RESULT_ROWS:
        raise SystemExit(f"Resultado posiblemente truncado ({len(rows)} filas): paginar.")
    if rbytes >= 0.9 * MAX_RESULT_BYTES:
        raise SystemExit(f"Resultado cerca del límite de bytes ({rbytes:,}): achicar el lote.")
    STATS["queries"] += 1
    STATS["read_rows"] += read
    STATS["result_bytes"] += rbytes
    STATS["wire_bytes"] += len(resp.content)
    STATS["server_s"] += int(s["elapsed_ns"]) / 1e9
    return rows


def in_list(projects: list[str]) -> str:
    return ", ".join("'" + p.replace("\\", "\\\\").replace("'", "\\'") + "'" for p in projects)


def batches(items: list[str], n: int):
    for i in range(0, len(items), n):
        yield items[i:i + n]


# ---------------------------------------------------------------------------- catálogo

def build_catalog(client: httpx.Client) -> tuple[list[str], int]:
    union: dict[str, None] = {}
    for y0, y1 in [(2017, 2021), (2022, 2026)]:  # 5 años × 100 = 500 filas por consulta
        rows = query(client, f"""
            SELECT toYear(date) AS y, project, sum(count) AS s FROM {PER_DAY}
            WHERE date BETWEEN '{y0}-01-01' AND '{y1}-12-31'
            GROUP BY y, project ORDER BY y, s DESC LIMIT 100 BY y""")
        for _, p, _ in rows:
            union.setdefault(p, None)
    n_union = len(union)
    filler = query(client, f"""
        SELECT project, sum(count) AS s FROM {PER_DAY}
        WHERE date BETWEEN '2025-01-01' AND '2025-12-31'
        GROUP BY project ORDER BY s DESC LIMIT 999""")
    for p, _ in filler:
        if len(union) >= CATALOG_SIZE:
            break
        union.setdefault(p, None)
    return list(union), n_union


# ---------------------------------------------------------------------------- descarga

def control_sums(client: httpx.Client, projects: list[str]) -> dict[str, tuple[int, int, str]]:
    """(días, suma, primera fecha, filas físicas) por paquete, calculado en el servidor.

    La tabla es un SummingMergeTree: hasta que el servidor fusiona partes, un mismo
    (paquete, día) puede estar en varias filas. Siempre se agrupa y se suma.
    """
    out = {}
    for b in batches(projects, 500):
        for p, n, s, first, phys in query(client, f"""
                SELECT project, uniqExact(date), sum(count), min(date), count() FROM {PER_DAY}
                WHERE project IN ({in_list(b)}) AND date >= '{START}' GROUP BY project"""):
            out[p] = (int(n), int(s), first, int(phys))
    return out


def fetch_daily(client: httpx.Client, projects: list[str]) -> dict[str, list[tuple[str, int]]]:
    series: dict[str, list[tuple[str, int]]] = {}
    for b in batches(projects, BATCH):
        rows = query(client, f"""
            SELECT project,
                   arrayStringConcat(arrayMap(x -> concat(toString(x.1), ':', toString(x.2)),
                                              arraySort(groupArray((date, n)))), ',')
            FROM (SELECT project, date, sum(count) AS n FROM {PER_DAY}
                  WHERE project IN ({in_list(b)}) AND date >= '{START}' GROUP BY project, date)
            GROUP BY project""")
        for p, packed in rows:
            series[p] = [(d, int(c)) for d, c in (kv.split(":") for kv in packed.split(","))]
    return series


def fetch_monthly(client: httpx.Client, projects: list[str]) -> dict[str, list[tuple[str, int]]]:
    """Serie mensual derivada en el servidor desde la tabla diaria (misma fuente → cuadra)."""
    series: dict[str, list[tuple[str, int]]] = {}
    for b in batches(projects, BATCH):
        rows = query(client, f"""
            SELECT project,
                   arrayStringConcat(arrayMap(x -> concat(toString(x.1), ':', toString(x.2)),
                                              arraySort(groupArray((m, n)))), ',')
            FROM (SELECT project, toStartOfMonth(date) AS m, sum(count) AS n FROM {PER_DAY}
                  WHERE project IN ({in_list(b)}) AND date >= '{START}' GROUP BY project, m)
            GROUP BY project""")
        for p, packed in rows:
            series[p] = [(d, int(c)) for d, c in (kv.split(":") for kv in packed.split(","))]
    return series


def verify(series: dict[str, list[tuple[str, int]]], sums: dict[str, tuple],
           daily: bool) -> None:
    missing = set(sums) - set(series)
    if missing:
        raise SystemExit(f"Faltan {len(missing)} paquetes en la descarga: {sorted(missing)[:5]}")
    for p, (n, s, *_) in sums.items():
        got = series[p]
        if sum(c for _, c in got) != s or (daily and len(got) != n):
            raise SystemExit(f"{p}: la serie no cuadra con la suma de control")


def fetch_python_monthly(client: httpx.Client, projects: list[str]) -> list[tuple[str, str, str, int]]:
    """(mes, paquete, python_minor, descargas): desglose mensual por versión de Python por paquete.

    Tabla de ~10.600 M de filas con clave que empieza por `project`: el filtro por paquete
    acota lo leído. Lotes chicos para no pasar 10.000 M de filas leídas ni 10 MB de resultado.
    """
    out = []
    for b in batches(projects, 25):
        sums = {p: int(s) for p, s in query(client, f"""
            SELECT project, sum(count) FROM {BY_PY}
            WHERE project IN ({in_list(b)}) AND date >= '{START}' GROUP BY project""")}
        rows = query(client, f"""
            SELECT project,
                   arrayStringConcat(arrayMap(x -> concat(toString(x.1), char(31), x.2, char(31),
                                                             toString(x.3)),
                                              groupArray((m, python_minor, n))), char(30))
            FROM (SELECT project, toStartOfMonth(date) AS m, python_minor, sum(count) AS n
                  FROM {BY_PY} WHERE project IN ({in_list(b)}) AND date >= '{START}'
                  GROUP BY project, m, python_minor)
            GROUP BY project""")
        got = {}
        for p, packed in rows:
            # python_minor trae valores basura con comas o barras (ver S2): separadores de control.
            items = [kv.split("\x1f") for kv in packed.split("\x1e")]
            got[p] = sum(int(n) for _, _, n in items)
            out += [(m, p, v, int(n)) for m, v, n in items]
        if got != sums:
            raise SystemExit("python_minor: la descarga no cuadra con la suma de control")
    return out


# ---------------------------------------------------------------------------- Parquet

def table(rows: list[tuple[str, str, int]], date_col: str) -> pa.Table:
    """Esquema del PRD: dato + procedencia por fila (constante dentro de un archivo)."""
    n = len(rows)
    captured = dt.datetime(2026, 11, 7, 3, 0, tzinfo=dt.UTC)
    return pa.table({
        date_col: pa.array([dt.date.fromisoformat(d) for d, _, _ in rows], pa.date32()),
        "project": pa.array([p for _, p, _ in rows], pa.string()),
        "count": pa.array([c for _, _, c in rows], pa.int64()),
        "source": pa.array(["clickpy"] * n, pa.string()),
        "acquisition": pa.array(["backfill"] * n, pa.string()),
        "captured_at": pa.array([captured] * n, pa.timestamp("s", tz="UTC")),
        "ingestion_run_id": pa.array(["2026-11-07T03:00:00Z-backfill"] * n, pa.string()),
    })


def write(t: pa.Table, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(t, path, compression="zstd", compression_level=9)
    return path.stat().st_size


def dir_size(path: Path) -> tuple[int, int]:
    files = [f for f in path.rglob("*.parquet")]
    return sum(f.stat().st_size for f in files), len(files)


def mb(n: float) -> str:
    return f"{n / 1e6:,.2f} MB"


# ---------------------------------------------------------------------------- main

def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "build/spikes/s5")
    shutil.rmtree(out, ignore_errors=True)
    t0 = time.monotonic()
    with httpx.Client(timeout=120) as client:
        catalog, n_union = build_catalog(client)
        print(f"## Catálogo\nunión top 100 anual 2017–2026: {n_union} paquetes; "
              f"completado a {len(catalog)} con el ranking de 2025")

        sums = control_sums(client, catalog)
        absent = [p for p in catalog if p not in sums]
        catalog = [p for p in catalog if p in sums]
        rows_daily = sum(v[0] for v in sums.values())
        phys = sum(v[3] for v in sums.values())
        first_years = defaultdict(int)
        for _, _, first, _ in sums.values():
            first_years[first[:4]] += 1
        print(f"sin datos desde {START}: {absent or 'ninguno'}")
        print("primer año con datos → paquetes: "
              + " ".join(f"{y}={n}" for y, n in sorted(first_years.items())))

        before = dict(STATS)
        t_daily = time.monotonic()
        daily = fetch_daily(client, catalog)
        verify(daily, sums, daily=True)
        cost_daily = {k: STATS[k] - before[k] for k in STATS} | {"wall_s": time.monotonic() - t_daily}

        before = dict(STATS)
        t_month = time.monotonic()
        monthly = fetch_monthly(client, catalog)
        verify(monthly, sums, daily=False)
        cost_month = {k: STATS[k] - before[k] for k in STATS} | {"wall_s": time.monotonic() - t_month}

        before = dict(STATS)
        t_py = time.monotonic()
        py = fetch_python_monthly(client, catalog)
        cost_py = {k: STATS[k] - before[k] for k in STATS} | {"wall_s": time.monotonic() - t_py}
        py_rows = len(py)

    rows_month = sum(len(v) for v in monthly.values())
    print(f"\n## Filas\ndiaria: {rows_daily:,} (paquete, día) · mensual: {rows_month:,} "
          f"(paquete, mes) · python_minor mensual por paquete: {py_rows:,}")
    print(f"filas físicas en ClickPy para la serie diaria: {phys:,} "
          f"(+{phys - rows_daily:,} sin fusionar: hay que agrupar y sumar)")

    print("\n## Costo del backfill (medido, modo array: 1 fila por paquete, lotes de "
          f"{BATCH})\nserie\tconsultas\tfilas_leídas\tresultado\ttransferido\tservidor_s\treloj_s")
    for name, c in [("diaria", cost_daily), ("mensual", cost_month),
                    ("python_minor mensual", cost_py)]:
        print(f"{name}\t{c['queries']}\t{c['read_rows']:,}\t{mb(c['result_bytes'])}\t"
              f"{mb(c['wire_bytes'])}\t{c['server_s']:.1f}\t{c['wall_s']:.1f}")
    print("Alternativa ingenua (1 fila por (paquete, fecha), páginas de 999): "
          f"diaria {-(-rows_daily // 999):,} consultas · mensual {-(-rows_month // 999):,} consultas")

    # --- Parquet: disposiciones
    flat_d = [(d, p, c) for p, s in daily.items() for d, c in s]
    flat_m = [(d, p, c) for p, s in monthly.items() for d, c in s]
    by_year: dict[str, list] = defaultdict(list)
    by_day: dict[str, list] = defaultdict(list)
    for r in flat_d:
        by_year[r[0][:4]].append(r)
        by_day[r[0]].append(r)

    sizes = {}
    sizes["diaria_1_archivo"] = write(table(sorted(flat_d, key=lambda r: (r[1], r[0])), "date"),
                                      out / "single/daily.parquet")
    for y, rows in by_year.items():
        write(table(sorted(rows, key=lambda r: (r[1], r[0])), "date"),
              out / f"by_year/clickpy/downloads_daily/year={y}/part-backfill.parquet")
    sizes["diaria_por_año"], n_year_files = dir_size(out / "by_year")
    sizes["mensual_1_archivo"] = write(table(sorted(flat_m, key=lambda r: (r[1], r[0])), "month"),
                                       out / "single/monthly.parquet")
    # Ingesta diaria "observed": un archivo nuevo por día (append-only). Se mide con los
    # últimos 30 días cerrados.
    last_days = sorted(by_day)[-31:-1]
    day_sizes = sorted(write(table(by_day[d], "date"),
                             out / f"by_day/clickpy/downloads_daily/date={d}/part.parquet")
                       for d in last_days)
    median_day = day_sizes[len(day_sizes) // 2]
    rows_per_day = sum(len(by_day[d]) for d in last_days) / len(last_days)
    t_py_tab = table([(m, p, c) for m, p, _, c in py], "month").append_column(
        "python_minor", pa.array([v for _, _, v, _ in py], pa.string()))
    sizes["python_1_archivo"] = write(t_py_tab.sort_by([("project", "ascending"),
                                                        ("month", "ascending")]),
                                      out / "single/python_minor_monthly.parquet")
    largest_file = max(f.stat().st_size for f in out.rglob("*.parquet"))

    print("\n## Parquet (zstd 9, con columnas de procedencia)\ndisposición\ttamaño\tbytes/fila")
    print(f"diaria, 1 archivo\t{mb(sizes['diaria_1_archivo'])}\t"
          f"{sizes['diaria_1_archivo'] / rows_daily:.2f}")
    print(f"diaria, 1 archivo por año ({n_year_files})\t{mb(sizes['diaria_por_año'])}\t"
          f"{sizes['diaria_por_año'] / rows_daily:.2f}")
    print(f"mensual, 1 archivo\t{mb(sizes['mensual_1_archivo'])}\t"
          f"{sizes['mensual_1_archivo'] / rows_month:.2f}")
    print(f"python_minor mensual por paquete, 1 archivo\t{mb(sizes['python_1_archivo'])}\t"
          f"{sizes['python_1_archivo'] / py_rows:.2f}")
    print(f"archivo diario de ingesta (mediana de 30 días, ~{rows_per_day:.0f} filas)\t"
          f"{median_day / 1e3:.1f} KB\t{median_day / rows_per_day:.2f}")
    print(f"archivo más grande generado: {mb(largest_file)} (límite duro de GitHub: 100 MB)")

    # --- Proyección (raw + normalized ≈ ×2; estrellas ≈ misma forma que descargas diarias)
    backfill = sizes["diaria_por_año"] + sizes["mensual_1_archivo"] + sizes["python_1_archivo"]
    per_year_obs = 365 * median_day
    print("\n## Proyección contra GitHub (repo sano < 1 GB; archivo > 100 MB bloqueado)")
    print("supuesto\thoy\t+5 años\t+10 años")
    for label, factor in [("descargas raw", 1), ("raw + normalized", 2),
                          ("raw + normalized + estrellas", 3)]:
        print(f"{label}\t{mb(factor * backfill)}\t{mb(factor * (backfill + 5 * per_year_obs))}\t"
              f"{mb(factor * (backfill + 10 * per_year_obs))}")
    print(f"archivos nuevos por año con 1 archivo por día y dataset: 365 × datasets "
          f"(~{median_day / 1e3:.0f} KB c/u)")
    print(f"\nTotal: {STATS['queries']} consultas, {time.monotonic() - t0:.0f} s; salida en {out}/")


if __name__ == "__main__":
    main()
