# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]
# ///
"""Spike S2 — ClickPy: descargas por versión menor de Python.

Uso:  uv run docs/spikes/s2_clickpy_python_versions.py

Misma instancia pública que S1 (usuario `play`, solo lectura). Pocas consultas agregadas;
no guarda nada en disco. Respalda docs/spikes/s2-clickpy-versiones-python.md.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict

import httpx

ENDPOINT = "https://sql-clickhouse.clickhouse.com/"
BY_PY = "pypi.pypi_downloads_per_day_by_version_by_python"  # date, project, version, python_minor, count
PER_DAY = "pypi.pypi_downloads_per_day"


# El usuario `play` tiene `read_overflow_mode=break` (máx. 10.000 M de filas leídas) y
# `result_overflow_mode=break` (máx. 1.000 filas de resultado): si se pasa, la respuesta llega
# TRUNCADA y sin error. Toda consulta verifica el resumen y falla ante un resultado parcial.
MAX_RESULT_ROWS = 1000


def query(client: httpx.Client, sql: str) -> list[list[str]]:
    resp = client.post(ENDPOINT, params={"user": "play"}, content=f"{sql} FORMAT TSV")
    if resp.is_error:
        raise SystemExit(f"ClickHouse {resp.status_code}: {resp.text[:500]}")
    summary = json.loads(resp.headers["X-ClickHouse-Summary"])
    read, total = int(summary["read_rows"]), int(summary["total_rows_to_read"])
    rows = [line.split("\t") for line in resp.text.splitlines()]
    if read < total:
        raise SystemExit(f"Lectura parcial ({read:,} de {total:,} filas): partir la consulta.")
    if len(rows) >= MAX_RESULT_ROWS:
        raise SystemExit(f"Resultado posiblemente truncado ({len(rows)} filas): paginar.")
    return rows


def show(title: str, header: str, rows: list[list[str]]) -> None:
    print(f"\n## {title}\n{header}")
    for row in rows:
        print("\t".join(str(c) for c in row))


# La tabla (~10.600 M de filas) supera el límite de lectura y su clave primaria empieza por
# `project`, así que se lee por rangos de nombre de proyecto (cada uno < 10.000 M de filas) y
# se suma en Python. Filtrar por fecha NO reduce lo leído.
CHUNKS = [("", "d"), ("d", "m"), ("m", "s"), ("s", None)]


def chunk_filter(lo: str, hi: str | None) -> str:
    cond = f"project >= '{lo}'"
    return cond if hi is None else f"{cond} AND project < '{hi}'"


def by_chunks(client: httpx.Client, select: str, where: str = "1") -> list[list[str]]:
    rows: list[list[str]] = []
    for lo, hi in CHUNKS:
        rows += query(client, select.format(where=f"({chunk_filter(lo, hi)}) AND ({where})"))
    return rows


def main() -> None:
    with httpx.Client(timeout=300) as client:
        show("Esquema", "columna\ttipo", [r[:2] for r in query(client, f"DESCRIBE {BY_PY}")])

        # (año, versión) -> descargas, y días con datos por año
        totals: dict[tuple[int, str], int] = defaultdict(int)
        for y, ver, n in by_chunks(client, f"""
                SELECT toYear(date), python_minor, sum(count) FROM {BY_PY}
                WHERE {{where}} GROUP BY 1, 2"""):
            totals[int(y), ver] += int(n)
        days: dict[int, set[str]] = defaultdict(set)
        for y, ds in by_chunks(client, f"""
                SELECT toYear(date), arrayStringConcat(arrayMap(toString, groupUniqArray(date)), ',')
                FROM {BY_PY} WHERE {{where}} GROUP BY 1"""):
            days[int(y)].update(ds.split(","))
        per_day = {int(y): int(n) for y, n in query(client, f"""
                SELECT toYear(date), sum(count) FROM {PER_DAY} GROUP BY 1""")}

        years = sorted({y for y, _ in totals})
        # Forma válida de versión menor; aún deja pasar basura rara (3.51, 3.92…): en el
        # producto se filtra contra la lista real de releases de CPython.
        valid = re.compile(r"^[23]\.[0-9]{1,2}$")
        cov, cons, shares = [], [], []
        for y in years:
            row = {v: n for (yy, v), n in totals.items() if yy == y}
            total = sum(row.values())
            ok = {v: n for v, n in row.items() if valid.match(v)}
            junk = sum(n for v, n in row.items() if v and not valid.match(v))
            cov.append([y, len(days[y]), round(total / 1e6), round(100 * row.get("", 0) / total, 1),
                        len(ok), f"{100 * junk / (total - row.get('', 0)):.4f}"])
            cons.append([y, round(total / 1e6), round(per_day[y] / 1e6),
                         round(100 * total / per_day[y], 1)])
            ok_total = sum(ok.values())
            top = sorted(ok.items(), key=lambda kv: -kv[1])
            shares.append([y, " ".join(f"{v}={100 * n / ok_total:.1f}" for v, n in top
                                       if 100 * n / ok_total >= 1)])

        show("Cobertura por año",
             "año\tdías\tdescargas_mm\t%_sin_versión\tversiones_válidas\t%_valores_basura",
             cov)
        show("Consistencia con la tabla diaria de S1", "año\tby_python_mm\tper_day_mm\tratio_%",
             cons)
        show("Cuota por versión y año (%, sobre versiones con forma válida, ≥ 1 %)",
             "año\tversiones", shares)

        month: dict[tuple[str, str], int] = defaultdict(int)
        for m, ver, n in by_chunks(client, f"""
                SELECT toStartOfMonth(date), python_minor, sum(count) FROM {BY_PY}
                WHERE {{where}} GROUP BY 1, 2""",
                where="date BETWEEN '2018-05-01' AND '2018-10-31' "
                      "AND NOT (date BETWEEN '2018-07-13' AND '2018-07-26')"):
            month[m, ver] += int(n)
        out = []
        for m in sorted({m for m, _ in month}):
            row = {v: n for (mm, v), n in month.items() if mm == m}
            ok_total = sum(n for v, n in row.items() if valid.match(v))
            out.append([m, round(100 * row.get("2.7", 0) / ok_total, 1),
                        round(100 * row.get("3.6", 0) / ok_total, 1),
                        round(100 * row.get("", 0) / sum(row.values()), 1)])
        show("Cuota 2.7 y 3.6 alrededor del salto de 2018 (%)", "mes\t2.7\t3.6\t%_sin_versión", out)


if __name__ == "__main__":
    main()
