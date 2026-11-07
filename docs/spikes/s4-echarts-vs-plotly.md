# Spike S4 — ECharts vs Plotly

> Fecha: 2026-11-07 · Script: `uv run docs/spikes/s4_charts_prototype.py` (2 consultas a ClickPy,
> 6 descargas de jsDelivr; páginas y capturas en `build/spikes/s4/`, no versionado)

## Pregunta

¿Qué librería de gráficos usa ecopy? Se compara peso, compatibilidad con la CSP estricta del PRD,
funciones necesarias y comportamiento en móvil, sobre un prototipo de **ranking** (barras
horizontales, top 15 de 2025) y **ficha** (línea mensual de `fastapi`, 95 meses, con zoom).

## Método

- Versiones fijas (≥ 2 semanas de antigüedad): ECharts **6.1.0** (builds `full`, `common`,
  `simple`) y Plotly.js **4.1.2** (`full`, `basic`). Plotly 4.2.0 se descartó por tener menos de 2
  semanas.
- Datos reales de ClickPy con el control de truncado de S2.
- Páginas con CSP estricta: `default-src 'none'; script-src 'self'; style-src 'self'; img-src
  'self' data:; …` — sin scripts ni estilos inline; datos en `<script type="application/json">`.
- Chrome headless (servidor local): estado de render, componentes presentes, violaciones de CSP
  (evento `securitypolicyviolation`) y capturas a 1280 px y 390 px.
- Peso medido con gzip -9 y brotli 11 (Cloudflare Pages sirve brotli).

## Resultados

**Peso** (brotli; la página completa suma ~1–3 KB de init, datos y CSS):

| Build | Crudo | gzip | brotli | Render con CSP estricta |
|---|---|---|---|---|
| ECharts full | 1.096 KB | 360 KB | **292 KB** | ok, sin violaciones |
| ECharts common | 698 KB | 234 KB | **195 KB** | ok, sin violaciones |
| ECharts simple | 489 KB | 165 KB | 140 KB | **parcial: sin title, tooltip ni dataZoom** |
| Plotly full | 4.721 KB | 1.442 KB | 1.089 KB | ok con `plotly.css`; intenta inyectar `<style>` |
| Plotly basic | 1.170 KB | 389 KB | **324 KB** | ok con `plotly.css`; intenta inyectar `<style>` |

**CSP.**
- ECharts no genera ninguna violación (renderer SVG).
- Plotly intenta inyectar un `<style>` inline (`style-src-elem`). Bloqueado, el gráfico se rompe:
  la barra de herramientas tapa el gráfico, el título se desplaza y desaparece el rangeslider.
  Se arregla enlazando `plotly.js/dist/plotly.css` (7 KB) desde 'self'; la violación se sigue
  registrando (intento bloqueado, sin efecto visible). Exige vigilar que ese CSS coincida con la
  versión de la librería.

**Funciones.** Ambas cubren ranking, línea temporal, tooltip, zoom y formato de números con
`Intl.NumberFormat('es')` (ECharts vía formatter; Plotly mostró `2B`/`500M` por defecto: requiere
`tickformat`/locale aparte). El build `simple` de ECharts no sirve (le faltan componentes);
`common` sí. `getOption()` conserva opciones de componentes que el build no trae: para detectarlo
hay que mirar el modelo (`getModel().getComponent(...)`).

**Móvil (390 px).** Ninguna queda lista sin ajustes: ECharts superpone las etiquetas del eje X del
ranking (se resuelve con `splitNumber`/`hideOverlap`); Plotly dibujó más ancho que la pantalla y
con la barra de herramientas sobre el título en la captura headless. Es trabajo de diseño de la
Etapa 5, no un descarte.

**Generación desde Python.** Las dos se alimentan con JSON generado desde Pydantic (decisión del
PRD); no hace falta `pyecharts` ni `plotly.py`.

## Decisión (confirmada por el usuario el 2026-11-07)

1. **ECharts 6.x, build `common`** (195 KB brotli): 40 % menos que Plotly basic (324 KB), ×5,6
   menos que Plotly full, y compatible con la CSP estricta sin parches.
2. Si la vista anual necesita un tipo de gráfico que `common` no trae (p. ej. treemap o heatmap),
   pasar a `full` (+97 KB) antes que armar un build a medida con Node (rompe el "Python-first").
3. La librería se **sirve desde el propio sitio** (versión fija, verificada con hash al construir),
   no desde un CDN: mantiene `script-src 'self'` y el sitio no depende de un tercero.
4. Renderer **SVG** (nítido, sin violaciones, captura de texto); revisar canvas solo si una vista
   con muchos puntos se vuelve lenta.

## Abierto

- Confirmar en la Etapa 3 qué tipos de gráfico pide la vista anual y si `common` alcanza.
- Accesibilidad (descripciones, contraste, modo oscuro) se evalúa con `impeccable` + `dataviz` en
  la Etapa 5.
