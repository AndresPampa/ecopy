# Spike S1 — ClickPy: cobertura y calidad de descargas diarias

> Fecha: 2026-11-06 · Script: `uv run docs/spikes/s1_clickpy_coverage.py` (~10 consultas agregadas)

## Pregunta

¿Desde qué fecha hay descargas diarias por paquete en ClickPy, con qué huecos y con qué calidad?
¿Desde qué año arranca el backfill y desde cuál las vistas anuales?

## Método

- Instancia pública de ClickHouse que usa ClickPy: `https://sql-clickhouse.clickhouse.com/`,
  usuario `play`, sin contraseña, interfaz HTTP. (El host `clickpy-clickhouse.clickhouse.com`
  rechazó la conexión TLS.)
- Tabla `pypi.pypi_downloads_per_day` (columnas `date`, `project`, `count`; ~1.110 M de filas).
- Base de datos `pypi` también expone, entre otras, `pypi_downloads_per_day_by_version_by_python`
  (insumo de S2) y `pypi_downloads_per_month`.
- Muestra: `requests`, `numpy`, `django`, `pandas`, `fastapi` (+ `pip` para cuotas).
- Calidad: días sin datos o con < 1 % de la mediana diaria del año; días con < 30 % de la mediana
  de ±15 días; promedios mensuales; cuota de la muestra alrededor de discontinuidades.

## Resultados

> Verificado contra los límites del usuario `play` (ver S2): todas las consultas leen la tabla
> completa y devuelven < 1.000 filas; el script falla si alguna se trunca.

**Rango.** 2016-01-22 → 2026-11-06 (hoy). 3.864 días con datos sobre 3.942 del rango.

**Huecos (sin datos):**
| Período | Días | Nota |
|---|---|---|
| 2016-03-06 → 2016-05-21 | 77 | 03-06 tiene 5 descargas en total; el resto, nada |
| 2019-04-26 → 2019-04-27 | 2 | |

**Ventana degradada.** 2018-07-13 → 2018-07-26: volúmenes de 3–30 % de lo normal (mínimo
2018-07-24: 130 mil descargas, 7.028 proyectos, frente a ~17 M diarios). Días sueltos bajos:
2018-04-17, 2019-04-13, 2019-04-25, 2019-04-28.

**Salto de régimen el 2018-07-27.** El promedio diario pasa de ~17–21 M (ene–jul 2018) a
~56–67 M (ago–dic 2018), ×3 de un día para el otro, y no vuelve. Causa no verificada (cambio en la
recolección de logs de PyPI, no en el uso real).

**El salto es uniforme en cuota.** Cuota mensual de la muestra, excluyendo la ventana degradada:

| Mes | requests | numpy | django | pandas | pip |
|---|---|---|---|---|---|
| 2018-06 | 1,38 % | 0,67 % | 0,18 % | 0,26 % | 3,96 % |
| 2018-07 | 1,31 % | 0,69 % | 0,16 % | 0,27 % | 3,91 % |
| 2018-08 | 1,34 % | 0,66 % | 0,14 % | 0,30 % | 3,76 % |
| 2018-09 | 1,43 % | 0,70 % | 0,13 % | 0,30 % | 3,85 % |

Las cuotas siguen su tendencia sin escalón → las métricas **relativas** (cuota, rankings, movers)
son comparables a través del salto; los **absolutos** no.

**Totales por año** (descargas, millones): 2016: 4.235 · 2017: 8.489 · 2018: 13.437 ·
2019: 37.567 · 2020: 67.824 · 2021: 126.718 · 2022: 199.525 · 2023: 284.570 · 2024: 526.074 ·
2025: 901.232 · 2026 (YTD a 11-06): 1.512.471. Proyectos con descargas: 87.767 (2016) →
1.060.498 (2026). El crecimiento ×350 en diez años confirma la advertencia del PRD sobre volumen.

**Muestra por paquete.** `requests`, `numpy`, `django`, `pandas`: desde 2016-01-22, presentes
todos los días con datos menos 2016-03-06. `fastapi`: desde 2018-12-08 (su primer release), sin
huecos salvo 2019-04-26/27. No hay huecos propios de un paquete: los huecos son globales.

**Día en curso.** Hay datos de hoy (2026-11-06: 5.873 M, frente a ~6.300–6.400 M de días hábiles
previos) → el día UTC en curso puede estar incompleto. No se midió si los días cerrados cambian
después.

## Decisión (confirmada por el usuario el 2026-11-06)

1. **Backfill crudo desde 2016-01-22** (todo lo que hay, es gratis): ~10 años, una sola fuente.
2. **Vistas anuales desde 2017** (primer año completo: 365 días) en métricas relativas.
   El PRD decía 2018; 2017 suma un año sin costo y el salto de 2018 no afecta las cuotas.
   2016 queda solo en fichas, marcado como parcial (empieza el 22-ene y le faltan 77 días).
3. **Volumen absoluto:** mostrar la discontinuidad del 2018-07-27 explícitamente; no calcular
   crecimientos de volumen que la crucen (2018 vs 2019). Va en la metodología.
4. **Marcar en el store, no borrar:** huecos y ventana degradada se registran como calidad del dato
   (flag), no se interpolan. Las series diarias muestran el hueco.
5. **Ingesta diaria hasta ayer (UTC)**; el día en curso no se ingesta.

## Abierto para etapas siguientes

- ¿Los días cerrados cambian después (reprocesos)? Medir en la Etapa 2 re-observando los últimos
  días en cada corrida (el store append-only lo permite sin perder nada).
- Causa del salto de 2018-07-27: buscar una fuente que lo documente para citarla en metodología.
- Términos de uso de ClickPy para republicar agregados (condiciona el plan B de R2).
