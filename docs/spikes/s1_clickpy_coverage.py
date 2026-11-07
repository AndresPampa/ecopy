# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]
# ///
"""Spike S1 — ClickPy: cobertura y calidad de descargas diarias.

Uso:  uv run docs/spikes/s1_clickpy_coverage.py

Consulta la instancia pública de ClickHouse que usa ClickPy (usuario `play`, sin contraseña,
solo lectura) con pocas consultas agregadas. No guarda nada en disco: imprime los resultados
que respaldan docs/spikes/s1-clickpy-cobertura.md.
"""

from __future__ import annotations

import json

import httpx

ENDPOINT = "https://sql-clickhouse.clickhouse.com/"
TABLE = "pypi.pypi_downloads_per_day"  # columnas: date, project, count
SAMPLE = ("requests", "numpy", "django", "pandas", "fastapi")


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
        print("\t".join(row))


def main() -> None:
    sample = ", ".join(f"'{p}'" for p in SAMPLE)
    with httpx.Client(timeout=120) as client:
        rango = query(client, f"""
            SELECT min(date), max(date), uniqExact(date),
                   dateDiff('day', min(date), max(date)) + 1
            FROM {TABLE}""")
        show("Rango global", "min\tmax\tdías_con_datos\tdías_del_rango", rango)
        first, last = rango[0][0], rango[0][1]

        show("Días sin datos o casi vacíos (< 1 % de la mediana diaria del año)",
             "fecha\tdescargas\tproyectos",
             query(client, f"""
                WITH daily AS (
                    SELECT date, sum(count) AS n, count() AS p
                    FROM {TABLE} GROUP BY date),
                med AS (SELECT toYear(date) AS y, median(n) AS m FROM daily GROUP BY y)
                SELECT d, n, p FROM (
                    SELECT toDate('{first}') + number AS d
                    FROM numbers(toUInt64(dateDiff('day', toDate('{first}'), toDate('{last}')) + 1))
                ) AS cal
                LEFT JOIN daily ON daily.date = cal.d
                LEFT JOIN med ON med.y = toYear(cal.d)
                WHERE n < med.m * 0.01
                ORDER BY d
                SETTINGS join_use_nulls = 0"""))

        show("Días anómalos (< 30 % de la mediana de ±15 días)",
             "fecha\tdescargas\tmediana_vecina",
             query(client, f"""
                WITH daily AS (SELECT date, sum(count) AS n FROM {TABLE} GROUP BY date)
                SELECT date, n, round(m) FROM (
                    SELECT date, n,
                           median(n) OVER (ORDER BY date
                               ROWS BETWEEN 15 PRECEDING AND 15 FOLLOWING) AS m
                    FROM daily)
                WHERE n < m * 0.3 ORDER BY date"""))

        show("Totales por año", "año\tdías\tdescargas_mm\tproyectos",
             query(client, f"""
                SELECT toYear(date) AS y, uniqExact(date),
                       round(sum(count) / 1e6), uniqExact(project)
                FROM {TABLE} GROUP BY y ORDER BY y"""))

        show("Promedio diario por mes 2018 (salto de régimen)", "mes\tpromedio_diario_mm",
             query(client, f"""
                SELECT toStartOfMonth(date) AS m, round(sum(count) / uniqExact(date) / 1e6, 1)
                FROM {TABLE} WHERE toYear(date) = 2018 GROUP BY m ORDER BY m"""))

        show("Transición julio 2018 (diario)", "fecha\tdescargas_mm\tproyectos",
             query(client, f"""
                SELECT date, round(sum(count) / 1e6, 2), uniqExact(project)
                FROM {TABLE} WHERE date BETWEEN '2018-07-15' AND '2018-08-05'
                GROUP BY date ORDER BY date"""))

        show("Muestra: cobertura por paquete", "proyecto\tprimer_día\túltimo_día\tdías\tdías_rango",
             query(client, f"""
                SELECT project, min(date), max(date), uniqExact(date),
                       dateDiff('day', min(date), max(date)) + 1
                FROM {TABLE} WHERE project IN ({sample})
                GROUP BY project ORDER BY project"""))

        show("Muestra: descargas por año (millones)", "proyecto\taño\tdescargas_mm",
             query(client, f"""
                SELECT project, toYear(date) AS y, round(sum(count) / 1e6, 1)
                FROM {TABLE} WHERE project IN ({sample})
                GROUP BY project, y ORDER BY project, y"""))

        show("Últimos 7 días (¿el día en curso está incompleto?)", "fecha\tdescargas_mm",
             query(client, f"""
                SELECT date, round(sum(count) / 1e6) FROM {TABLE}
                WHERE date >= today() - 7 GROUP BY date ORDER BY date"""))

        # ¿El salto de 2018-07-27 es uniforme? Si las cuotas no cambian, las métricas
        # relativas (cuota por categoría, rankings) son comparables a través del salto.
        degraded = "date BETWEEN '2018-07-13' AND '2018-07-26'"
        window = f"date BETWEEN '2018-05-01' AND '2018-10-31' AND NOT ({degraded})"
        show("Cuota mensual (%) alrededor del salto de 2018", "mes\trequests\tnumpy\tdjango\tpandas\tpip",
             query(client, f"""
                WITH tot AS (
                    SELECT toStartOfMonth(date) AS m, sum(count) AS t
                    FROM {TABLE} WHERE {window} GROUP BY m)
                SELECT p.m,
                       round(100 * sumIf(n, project = 'requests') / any(t), 2),
                       round(100 * sumIf(n, project = 'numpy') / any(t), 2),
                       round(100 * sumIf(n, project = 'django') / any(t), 2),
                       round(100 * sumIf(n, project = 'pandas') / any(t), 2),
                       round(100 * sumIf(n, project = 'pip') / any(t), 2)
                FROM (
                    SELECT toStartOfMonth(date) AS m, project, sum(count) AS n
                    FROM {TABLE}
                    WHERE {window} AND project IN ('requests', 'numpy', 'django', 'pandas', 'pip')
                    GROUP BY m, project) AS p
                JOIN tot ON tot.m = p.m
                GROUP BY p.m ORDER BY p.m"""))


if __name__ == "__main__":
    main()
