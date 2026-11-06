# ecopy

**The Python ecosystem, year by year.**

ecopy muestra cómo evoluciona el ecosistema Python desde 2018: qué librerías crecen, cuáles pierden
terreno, qué versiones del lenguaje se adoptan y qué categorías ganan peso. Es un sitio estático,
bilingüe (EN/ES), que se regenera una vez al día y se publicará en `ecopy.pages.dev`.

> **Estado:** en planificación. El PRD está cerrado; todavía no hay código del producto.
> Ver [`docs/prd.md`](docs/prd.md) y [`docs/HANDOFF.md`](docs/HANDOFF.md).

## Qué va a ofrecer (MVP)

- **Vista anual:** cuota de descargas por categoría, movers, recién llegados, adopción de versiones
  de Python, línea de tiempo del lenguaje y volumen total (con advertencia sobre inflación por CI).
  El año en curso se compara como YTD contra el mismo período del año anterior.
- **Fichas de librerías:** un catálogo de ~500 paquetes (unión del top 100 de cada año desde 2018
  + lista curada por categoría) con su serie histórica de descargas.
- **Comparador simple** entre librerías.
- **Releases de Python** en una línea de tiempo.
- **Metodología:** fuentes, fórmulas, sesgos conocidos y versión metodológica de cada ranking.
- **Estrellas de GitHub,** si se confirma una fuente histórica viable.

Principios: los rankings de años cerrados se congelan, no hay puntajes combinados opacos, los
renombres de paquetes se enlazan pero no se suman, y cada dato guarda su procedencia.

## Cómo funciona

```
GitHub Actions (cron diario)
  → ingesta en Python (ClickPy; BigQuery como respaldo)
  → Parquet append-only + DuckDB
  → cálculo de métricas
  → render HTML (Jinja2 + ECharts + SVG)
  → Cloudflare Pages
```

Sin servidor en runtime y con presupuesto cero: los datos cambian una vez al día y todo es de
lectura, así que un sitio pre-generado alcanza.

Módulos previstos: `sources`, `store`, `catalog`, `metrics`, `site` y `cli`.

## Roadmap

- **Fase 0 — spikes de validación:** cobertura histórica de ClickPy, desglose por versión de Python,
  fuente de histórico de estrellas, ECharts vs Plotly, tamaño real del Parquet.
- **MVP:** lo descrito arriba.
- **Fase 3:** Trending y Seguridad (las estrellas se capturan a diario desde el día 1).
- **Fase 4:** cuentas y encuestas.

## Fuentes de datos

- Descargas de PyPI (linehaul), consultadas vía [ClickPy](https://clickpy.clickhouse.com/).
- Dataset público de PyPI en BigQuery, como respaldo reproducible.
- Releases de Python y, si es viable, conteos de estrellas de GitHub (nunca identidades de usuarios).

## Documentación

- [`docs/prd.md`](docs/prd.md) — requisitos del producto, historias de usuario y decisiones.
- [`docs/HANDOFF.md`](docs/HANDOFF.md) — estado actual, decisiones clave y próximos pasos.

## Licencia

[MIT](LICENSE). Los datos mostrados pertenecen a sus fuentes (PyPI/linehaul, ClickPy, GitHub) y se
publican con atribución.
