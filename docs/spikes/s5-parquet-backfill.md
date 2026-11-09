# Spike S5 — Tamaño del Parquet y costo del backfill

> Fecha: 2026-11-07 · Script: `uv run docs/spikes/s5_parquet_backfill.py` (64 consultas a ClickPy,
> ~37 s; Parquet de prueba en `build/spikes/s5/`, no versionado). Corrido 3 veces con cifras estables.

## Pregunta

¿Cuánto ocupa en Parquet el histórico de ~500 paquetes desde 2016-01-22 y cuánto crece por año?
¿Alcanza el repo de GitHub o hace falta el plan B (R2)? ¿Cuánto cuesta el backfill con los límites
de la instancia pública de ClickPy, y conviene guardar la serie diaria o la mensual?

## Método

- **Catálogo de prueba (500):** unión del top 100 de cada año 2017–2026 (como el PRD) completada
  con el ranking de 2025 hasta 500, en lugar de la lista curada. Sesgo hacia paquetes con historia
  larga → **cota superior** del tamaño (315 de 500 tienen datos desde 2016).
- **Límites del usuario `play`** leídos de `system.settings`: `max_result_rows=1000`,
  `max_result_bytes=10 MB`, `max_rows_to_read=10.000 M` (todos con `break`: truncan sin error),
  `max_execution_time=60 s`, `max_network_bandwidth=25 MB/s`, `readonly=1`.
- **Descarga en modo array:** una fila por paquete con su serie empaquetada (`groupArray`), lotes de
  50 paquetes (≈ 5 MB de resultado por consulta). Cada lote se cuadra contra sumas de control
  calculadas en el servidor (días distintos y descargas por paquete); el script aborta si no cuadra.
- **Series:** diaria (`pypi_downloads_per_day`, clave `project, date`), mensual derivada de la misma
  tabla en el servidor, y desglose mensual por versión de Python por paquete
  (`pypi_downloads_per_day_by_version_by_python`, lotes de 25).
- **Parquet:** pyarrow, zstd nivel 9, con las columnas de procedencia del PRD (`source`,
  `acquisition`, `captured_at`, `ingestion_run_id`). Disposiciones: un archivo, uno por año, y un
  archivo por día (ingesta diaria append-only, medida sobre los últimos 30 días cerrados).

## Resultados

**Filas (500 paquetes, 2016-01-22 → 2026-11-06):**

| Serie | Filas |
|---|---|
| Diaria (paquete, día) | 1.656.388 |
| Mensual (paquete, mes) | 55.640 |
| Versión de Python mensual por paquete (paquete, mes, `python_minor`) | 634.996 |

El catálogo del PRD da menos de lo esperado: **la unión del top 100 anual son solo 213 paquetes**;
los ~290 restantes tienen que salir de la lista curada (dato para la Etapa 2).

**Costo del backfill (medido):**

| Serie | Consultas | Filas leídas | Transferido | Tiempo |
|---|---|---|---|---|
| Diaria | 10 | 28,9 M | 29 MB | 6 s |
| Mensual | 10 | 28,9 M | 1 MB | 3 s |
| Python mensual por paquete | 40 | 1.006 M | 13 MB | 16 s |

Con una fila por (paquete, fecha) y páginas de 999 filas, la diaria serían **1.659 consultas** (y
cada página con `OFFSET` relee lo anterior); la mensual, 56. El modo array lo vuelve trivial: el
límite de 1.000 filas deja de importar y el que manda pasa a ser el de 10 MB de resultado.

**Tamaño en Parquet (zstd 9):**

| Disposición | Tamaño | Bytes/fila |
|---|---|---|
| Diaria, 1 archivo | 6,27 MB | 3,8 |
| Diaria, 1 archivo por año (11) | **7,30 MB** | 4,4 |
| Mensual, 1 archivo | 0,30 MB | 5,5 |
| Python mensual por paquete, 1 archivo | 2,65 MB | 4,2 |
| Archivo de un día de ingesta (~500 filas, mediana de 30 días) | 8,6 KB | 17,3 |

Archivo más grande: 6,3 MB (GitHub avisa a 50 MB y bloquea a 100 MB). Las columnas de procedencia
cuestan casi nada (constantes por archivo → diccionario/RLE). El archivo diario paga ~4× por fila
por los metadatos del Parquet: **~3,1 MB por año** de ingesta diaria.

**Proyección contra GitHub** (backfill = diaria por año + mensual + Python por paquete = 10,3 MB;
"normalized" ≈ duplicar raw; "estrellas" ≈ una serie diaria más del mismo tamaño, supuesto):

| Supuesto | Hoy | +5 años | +10 años |
|---|---|---|---|
| Descargas raw | 10 MB | 26 MB | 42 MB |
| Raw + normalized | 21 MB | 52 MB | 83 MB |
| Raw + normalized + estrellas | 31 MB | 78 MB | 125 MB |

Incluso el peor supuesto a 10 años queda en ~13 % del "repo sano < 1 GB". Como el store es
append-only, la historia de git ≈ suma de los archivos (Parquet ya viene comprimido; git no gana
nada, pero tampoco hay reescrituras que dupliquen).

**Hallazgos sobre ClickPy (no reintentar a ciegas):**

1. **La tabla diaria tiene filas duplicadas por (paquete, día)** — es un `SharedSummingMergeTree` y
   las partes recientes aún no están fusionadas (4.000 filas extra en el catálogo; `requests` tiene
   4 filas para 2026-11-06). **Siempre `GROUP BY project, date` + `sum(count)`**, nunca leer filas
   crudas ni contar días con `count()`.
2. **El resumen `X-ClickHouse-Summary` sale con el primer bloque** salvo que se pida
   `wait_end_of_query=1`: sin él, `result_rows`/`result_bytes` llegan en 0 y `read_rows` puede ser
   parcial. El control de S1/S2 sigue valiendo para lo que verifica (filas reales del cuerpo y
   agregaciones, que leen todo antes de emitir), pero el adaptador debe usar `wait_end_of_query=1`.
3. **El límite de 10 MB no corta de forma fiable:** en la primera corrida, lotes de 100 paquetes
   (~12,9 MB de resultado según `result_bytes` medido después) llegaron completos y cuadraron con
   las sumas de control; el corte con `break` parece aplicarse entre bloques. No es una garantía: hay que mantener los lotes bien por
   debajo (50 → ~5 MB) y **cuadrar cada descarga contra sumas de control en el servidor**, que es la
   única defensa que no depende del resumen.
4. `python_minor` trae valores basura con comas y barras (ya visto en S2): al empaquetar, usar
   separadores de control y partir el cuerpo con `split("\n")`, no `splitlines()`.

## Decisión (confirmada por el usuario el 2026-11-07)

1. **Alcanza el repo; no se activa R2.** Backfill ≈ 10 MB y ~3 MB/año por serie diaria; a 10 años
   ≤ 125 MB con supuestos generosos. Revisar si `data/` supera 500 MB o algún archivo pasa 50 MB.
2. **Guardar la serie diaria, no la mensual.** Cuesta 7 MB y 10 consultas: la diferencia con la
   mensual es irrelevante, y la diaria es necesaria para YTD vs mismo período, los flags de huecos y
   la ventana degradada de 2018. La mensual se deriva en `metrics`.
3. **Disposición:** backfill en un archivo por año (`year=YYYY/part-backfill.parquet`); ingesta
   diaria en un archivo nuevo por día y dataset (append-only, ~9 KB).
4. **Adaptador de ClickPy (Etapa 1):** modo array por lotes de ≤ 50 paquetes, `wait_end_of_query=1`,
   `GROUP BY` + `sum` siempre, cuadre contra sumas de control por lote, y el control de truncado de
   S2. Agregar los hallazgos 1–3 al PRD (sección Fuentes).
5. **Versión de Python:** la historia 5 (adopción global) usa el agregado de todo PyPI (S2, pocas
   filas). El desglose por paquete (2,65 MB) no lo pide ninguna historia del MVP: no se guarda por
   ahora; si se pide después, es barato.

## Abierto

- La lista curada debe aportar ~290 paquetes (la unión del top 100 anual da 213).
- Para la cuota por categoría hace falta el denominador: total diario de PyPI (1 fila por día,
  despreciable). Confirmarlo en la Etapa 2.
- ~3.650 archivos por dataset a 10 años con un archivo por día: medir el tiempo de lectura de
  DuckDB en la Etapa 2; compactar contradice la inmutabilidad, así que cualquier consolidación
  sería un archivo nuevo versionado.
- Estrellas: tamaño estimado, no medido (el backfill de S3 se ejecuta en la Etapa 2).
