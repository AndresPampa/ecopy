# Spike S2 — ClickPy: descargas por versión menor de Python

> Fecha: 2026-11-06 · Script: `uv run docs/spikes/s2_clickpy_python_versions.py` (~13 consultas, ~30 s)

## Pregunta

¿ClickPy desglosa las descargas por versión menor de Python, desde cuándo y con qué calidad?
¿Se puede construir la historia 5 (adopción de versiones de Python por año)?

## Método

- Tabla `pypi.pypi_downloads_per_day_by_version_by_python` (`date`, `project`, `version`,
  `python_minor`, `count`; ~10.600 M de filas; clave `project, version, date, python_minor`).
- La versión es la del intérprete que hizo la descarga (dato de linehaul).
- Lectura por 4 rangos de nombre de proyecto, sumados en Python (ver "Límites" abajo).
- Validación de completitud: el total por año debe coincidir con la tabla diaria de S1.

## Resultados

**Sí hay desglose, desde el primer día de datos (2016-01-22)**, con los mismos huecos que S1.

**Completitud:** el total por año coincide al 100 % con `pypi_downloads_per_day` en 2016–2025
(2026 difiere en 0,01 % por la carga en vivo del día). Ninguna descarga se pierde en el desglose.

**Calidad:**
| Año | Sin versión | Valores basura* |
|---|---|---|
| 2016 | 17,2 % | 0,07 % |
| 2017 | 11,1 % | 0,02 % |
| 2018 | 8,2 % | 0,02 % |
| 2019–2026 | 3,7–9,4 % | < 0,0001 % |

\* Valores con forma no válida (p. ej. `sys.version_info(...)`, `X.XX`, `main`); además pasan el
filtro de forma algunos imposibles (`3.51`, `3.92`), con peso despreciable.

**Cuota por versión** (% de las descargas con versión válida, ≥ 1 %):
| Año | Principales |
|---|---|
| 2017 | 2.7 = 80,6 · 3.5 = 7,4 · 3.6 = 5,4 · 3.4 = 4,3 |
| 2018 | 2.7 = 64,5 · 3.6 = 20,4 · 3.5 = 8,6 |
| 2019 | 2.7 = 48,4 · 3.6 = 25,6 · 3.7 = 13,3 |
| 2020 | 3.7 = 34,0 · 3.6 = 23,6 · 2.7 = 22,4 · 3.8 = 11,1 |
| 2021 | 3.7 = 43,4 · 3.8 = 20,2 · 3.6 = 18,4 · 2.7 = 8,6 |
| 2022 | 3.7 = 35,4 · 3.8 = 31,1 · 3.9 = 12,6 |
| 2023 | 3.8 = 27,2 · 3.7 = 25,4 · 3.9 = 18,6 · 3.10 = 14,4 |
| 2024 | 3.10 = 24,6 · 3.9 = 18,4 · 3.11 = 16,4 · 3.8 = 15,5 |
| 2025 | 3.11 = 25,2 · 3.10 = 23,9 · 3.12 = 17,4 |
| 2026 YTD | 3.12 = 31,8 · 3.11 = 21,4 · 3.10 = 16,1 · 3.13 = 13,9 · 3.14 = 6,0 |

La serie es coherente con la historia conocida (Python 2.7 dominante hasta 2019; fin de soporte
de 2.7 en 2020). El salto de 2018-07-27 tampoco altera estas cuotas (2.7: 63,7 % en julio,
63,4 % en agosto).

## Límites de la instancia pública (afectan a todo el proyecto)

Medidos con el encabezado `X-ClickHouse-Summary` y `system.settings` del usuario `play`:

- `max_rows_to_read = 10.000 M` con `read_overflow_mode = break`: si una consulta debe leer más,
  **devuelve un resultado parcial sin error**. Esta tabla (10.600 M) siempre lo supera en una sola
  consulta; filtrar por fecha no ayuda (la clave empieza por `project`). Filtrar por `project`
  sí: un paquete lee ~2 M de filas.
- `max_result_rows = 1.000` con `result_overflow_mode = break`: un resultado de más de 1.000 filas
  **se corta sin error** en un borde de bloque (p. ej. la serie diaria de `numpy` devolvió 3.749
  de 3.863 filas).
- `max_execution_time = 60 s`, `readonly = 1` (no se pueden cambiar settings).
- La primera versión de este spike, sin control, dio cuotas con errores de ~1 punto y totales
  ~80 % de los reales.

**Regla para el adaptador `sources` (Etapa 1+):** toda consulta verifica
`read_rows == total_rows_to_read` y menos de 1.000 filas de resultado, y si no, falla; las series
largas se paginan; las tablas grandes se leen por rangos de `project`. Los scripts de S1 y S2 ya
aplican este control (S1 lo pasa sin cambios en sus resultados).

## Decisión

1. **Historia 5 confirmada:** la vista anual incluye adopción de versiones de Python desde 2017.
2. Granularidad: **mensual a nivel ecosistema** (≈ 130 meses × ~20 versiones), no diaria.
3. Versiones válidas = lista real de releases de CPython (fuente de releases de la Etapa 4); el
   resto se agrupa en "otra"; "sin versión" se muestra aparte, no se reparte.
4. La metodología explica que es la versión del intérprete que descarga (incluye CI).

## Abierto

- S5 debe sumar el costo del backfill bajo el límite de 1.000 filas: una serie diaria por paquete
  (~3.900 días) son ≥ 4 consultas; ~500 paquetes ≈ 2.000 consultas. Evaluar series mensuales
  para el histórico y diarias solo para lo reciente.
