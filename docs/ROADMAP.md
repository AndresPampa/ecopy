# Roadmap — ecopy

> Mapa del proyecto por etapas. Estado entre sesiones → `docs/HANDOFF.md`; qué construir →
> `docs/prd.md`. Solo la etapa en curso se detalla; las demás son una línea.
>
> **Flujo (proyecto de una persona):** cada etapa = una rama `etapa-N-<tema>` → commit(s) → PR
> a `main`. Sin issues ni OpenSpec. Un slice se tilda cuando su resultado está en la rama
> (verificado); la etapa se colapsa en *Shipped* al mergear.

## Etapas

- 🚧 **Etapa 0 — Spikes de validación:** las incógnitas que condicionan el PRD quedan respondidas
  con evidencia y una decisión escrita.
- 📋 **Etapa 1 — Tracer bullet:** un paquete, de ClickPy a una página publicada en
  `ecopy.pages.dev` vía GitHub Actions, atravesando `sources → store → metrics → site → cli`.
- 📋 **Etapa 2 — Datos completos:** (incluye cerrar la taxonomía de categorías y tags en el YAML) backfill desde 2016-01-22 (vistas desde 2017), catálogo ~500 (YAML + top 100 anual,
  renombres), procedencia por fila, ingesta diaria y validación con "Actualización fallida".
- 📋 **Etapa 3 — Vista anual:** cuota por categoría, movers, recién llegados, adopción de versiones,
  línea de tiempo, volumen total con advertencia, YTD y rankings congelados.
- 📋 **Etapa 4 — Librerías y comparador:** fichas con series y sparklines, comparador, releases de
  Python, estrellas, páginas de dominio/categoría y filtro por tags.
- 📋 **Etapa 5 — Publicación del MVP:** EN/ES completo, metodología, CSP/`_headers`, accesibilidad
  y diseño (`impeccable` + `dataviz`).
- 📋 **Después del MVP:** Trending y Seguridad (Fase 3); cuentas y encuestas (Fase 4).

## Etapa en curso — Etapa 0: Spikes de validación

**Rama:** `etapa-0-spikes`

**Objetivo:** que cada incógnita de "Further Notes" del PRD tenga una respuesta medida y una
decisión, antes de escribir código del producto.

**Criterios de cierre** (todos verificables):
1. Cada spike tiene su informe en `docs/spikes/` con: pregunta, método, resultado (cifras/consultas
   reales) y decisión.
2. Los scripts son reproducibles con `uv run` (dependencias inline, sin configurar el proyecto aún).
3. El PRD y el handoff reflejan las decisiones (p. ej., si se cae la historia 5 o la 17).
4. Ningún script guarda identidades de usuarios de GitHub ni credenciales.

**Slices** (orden previsto):
- [x] **S1 — ClickPy: cobertura y calidad.** Fecha mínima con datos diarios por paquete, huecos y
  consistencia, sobre una muestra (`requests`, `numpy`, `django`, `pandas`, `fastapi`). Decide el
  año inicial del backfill. *Habilita S2, S4 y S5.* → informe en
  `docs/spikes/s1-clickpy-cobertura.md`; decisión: datos desde 2016-01-22, vistas anuales
  desde 2017 (confirmado 2026-11-06).
- [x] **S2 — ClickPy: desglose por versión de Python.** ¿Hay descargas por versión menor de Python,
  y desde cuándo? Decide la historia 5 (adopción de versiones). *Depende de S1.* → sí, desde 2016;
  historia 5 confirmada (`docs/spikes/s2-clickpy-versiones-python.md`).
- [x] **S3 — Fuente del histórico de estrellas.** Confirmar si existe un endpoint de historia; si
  no, medir `starred_at` del listado de stargazers en un repo chico y uno grande (límite de
  paginación, requests por repo, costo para ~500 repos). Decide la historia 17. *Independiente.* → el endpoint
  existe y cuadra exacto; informe en `docs/spikes/s3-github-estrellas.md`; decisión confirmada 2026-11-07.
- [x] **S4 — ECharts vs Plotly.** Prototipo de un ranking + una ficha con datos de S1; medir peso
  transferido (gzip) y legibilidad. Decide la librería de gráficos. *Depende de S1.* → ECharts
  `common` 195 KB vs Plotly basic 324 KB (brotli), sin violaciones de CSP; informe en
  `docs/spikes/s4-echarts-vs-plotly.md`; decisión: ECharts 6 `common`, servido desde el sitio
  (confirmado 2026-11-07).
- [ ] **S5 — Tamaño del Parquet.** Con datos reales de S1, proyectar ~500 paquetes × diario desde el
  año inicial; comparar con los límites de GitHub (archivos >100 MB bloqueados; repo sano <1 GB).
  Decide si alcanza el repo o se activa el plan B (R2). Incluir el costo del backfill con
  el límite de 1.000 filas por consulta (ver S2). *Depende de S1.* → backfill ≈ 10 MB (diaria 7,3 MB,
  10 consultas en modo array), ~3 MB/año de ingesta; alcanza el repo, sin R2; informe en
  `docs/spikes/s5-parquet-backfill.md`; decisión pendiente de confirmar.
- [ ] **S6 — Cloudflare Pages (manual, usuario).** Crear el proyecto y confirmar `ecopy.pages.dev`.
  *Independiente; necesario recién en la Etapa 1.*

## Shipped

_(vacío)_
