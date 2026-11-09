# Spike S7 — ClickPy: correcciones de días cerrados y umbrales de validación

> Fecha: 2026-11-09 · Script: `uv run python docs/spikes/s7_clickpy_revisions_thresholds.py`
> (~30 consultas de solo lectura). Línea de base: Parquet de S5 en `build/spikes/s5/` (no versionado;
> al regenerarlos cambia la captura). Para repetirlo más adelante sirve también `data/`.

## Preguntas

¿ClickPy corrige días ya cerrados? ¿Qué umbrales puede usar `validate` sin falsos positivos? ¿Hay
que compactar los archivos diarios del store?

## Resultados

- **Correcciones:** 0 de 1.656.388 filas cambiaron y ninguna desapareció, para 500 paquetes de
  2016-01-22 a 2026-11-06, entre la captura de S5 (2026-11-07 23:14 UTC) y 2026-11-09 15:40 UTC.
  Los totales anuales 2016–2025 coinciden con los de S1, en millones.
- **Último día:** el 2026-11-06, que S1 marcó como posiblemente incompleto, sigue en 5.873 M. Era
  viernes, y el viernes anterior dio 5.633 M. A las 15:40 UTC el último día disponible era ayer.
- **Dispersión diaria** (día / mediana de los 4 mismos días de semana previos): desde 2020, 2.504
  días entre 0,529 (2020-01-01) y 1,494. Antes de 2020, por debajo de 0,5: 2016-12-08, 2017-05-11,
  2018-04-17, 2018-07-11→26 (días hábiles), 2019-04-13, 2019-04-25 y 2019-04-28.
- **Sin explicar:** desde 2026-08-25 el total cae ~36 % de un día para el otro (6.283 M diarios del
  10 al 23 de agosto, 4.002 M del 25 de agosto al 7 de septiembre) y se recupera despacio (~0,92 del
  nivel previo en noviembre). La cuota del catálogo casi no cambia (67,0 % → 67,7 %), pero
  `weaviate-client` cae ×0,12 y `litellm` y `textual` ×0,16. No cumple la regla y no se marca.
- **Versiones contra total:** iguales en 125 de 130 meses. Difieren 2026-04 (+114 M), 06, 07, 08 y
  10 (−4,9 M), ~0,08 % como máximo estimado. Son meses cerrados: corrige la explicación de S2.
- **Huecos por paquete:** 369 de 500 paquetes tienen días sin filas dentro de su historia (2.834
  días; `uv`, 521). Desde 2025 solo 2 paquetes, ambos nuevos. Corrige la conclusión de S1 con 5
  paquetes: un día sin filas de un paquete no es un hueco de la fuente.
- **Lectura del store:** 3.651 archivos, 3,48 M de filas: 3,6 s para 500 paquetes y 0,16 s para el
  último día por paquete. No hace falta compactar (abierto de S5).
- **Costos:** denominador, 1 consulta de 0,7 s. Versiones globales, 4 rangos + 4 controles, ~23 s y
  10.644 M de filas leídas por pasada.

## Límites

Cubre una ventana de ~40 h y un solo par de capturas. No dice nada de reprocesos raros a más largo
plazo ni de las primeras horas tras cerrar un día. Por eso la ingesta reobserva los últimos 7 días
y cuenta las correcciones en `data/runs/`.

## Decisión (confirmada por el usuario el 2026-11-09)

Ver `docs/design/etapa-2-datos-completos.md`, decisiones 1, 4, 5 y 9.
