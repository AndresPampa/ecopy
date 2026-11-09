# Roadmap — ecopy

> Mapa del proyecto por etapas. Estado entre sesiones → `docs/HANDOFF.md`; qué construir →
> `docs/prd.md`. Solo la etapa en curso se detalla; las demás son una línea.
>
> **Flujo (proyecto de una persona):** cada etapa = una rama `etapa-N-<tema>` → commit(s) → PR
> a `main`. Sin issues ni OpenSpec. Un slice se tilda cuando su resultado está en la rama
> (verificado); la etapa se colapsa en *Shipped* al mergear.

## Etapas

- ✅ **Etapa 0 — Spikes de validación:** las incógnitas que condicionan el PRD quedan respondidas
  con evidencia y una decisión escrita.
- ✅ **Etapa 1 — Tracer bullet (local):** un paquete, de ClickPy a una página generada y servida
  en local, atravesando `sources → store → metrics → site → cli`. Sin Actions ni Cloudflare.
  Las Etapas 2–4 también se prueban en local.
- 📋 **Etapa 2 — Datos completos:** (incluye cerrar la taxonomía de categorías y tags en el YAML) backfill desde 2016-01-22 (vistas desde 2017), catálogo ~500 (YAML + top 100 anual,
  renombres), procedencia por fila, ingesta diaria y validación con "Actualización fallida".
- 📋 **Etapa 3 — Vista anual:** cuota por categoría, movers, recién llegados, adopción de versiones,
  línea de tiempo, volumen total con advertencia, YTD y rankings congelados.
- 📋 **Etapa 4 — Librerías y comparador:** fichas con series y sparklines, comparador, releases de
  Python, estrellas, páginas de dominio/categoría y filtro por tags.
- 📋 **Etapa 5 — Publicación del MVP:** EN/ES completo, metodología, CSP/`_headers`, accesibilidad
  y diseño (`impeccable` + `dataviz`); GitHub Actions (cron diario) y despliegue en Cloudflare
  Pages, incluido S6 (crear el proyecto y confirmar `ecopy.pages.dev`, lo hace el usuario).
- 📋 **Después del MVP:** Trending y Seguridad (Fase 3); cuentas y encuestas (Fase 4).

## Próxima etapa — Etapa 2: Datos completos

**Rama sugerida:** `etapa-2-datos-completos`

**Objetivo:** pasar del tracer bullet de un paquete al dataset real: catálogo de ~500 paquetes,
backfill desde 2016-01-22, ingesta incremental, validación y calidad del dato. Todo en local.

**Diseño:** `docs/design/etapa-2-datos-completos.md` (aprobado 2026-11-09).

**Slices (TDD):**

- [x] 1. Calidad y estados de período: `quality`, `metrics`, etiquetas en `site`; mediciones a `docs/spikes/`.
- [x] 2. Store multi-dataset: escritura de cambios y `last_days`.
- [x] 3. Fuentes nuevas: totales de PyPI, versiones de Python, top 100.
- [x] 4. Catálogo: `catalog`, taxonomía, `ecopy catalog refresh|check`.
- [x] 5. Ingesta real: `validate`, `pipeline.ingest`, `data/runs/`, multi paquete.
- [x] 6. "Actualización fallida": aviso EN/ES y humo end-to-end.
- [ ] 7. Contenido del catálogo: 500 librerías en borrador; falta la revisión del usuario.
- [ ] 8. Corrida real: backfill, reobservación y build hechos; falta reobservar en un día posterior.

## Shipped

- ✅ **Etapa 1 — Tracer bullet local** (PR #3, 2026-11-09): `ingest → build → serve` de punta a
  punta con `fastapi`; ficha EN/ES con ECharts y CSP estricta. Diseño en
  `docs/design/etapa-1-tracer-bullet.md`.
- ✅ **Etapa 0 — Spikes de validación** (PR #2, 2026-11-07): S1–S5 con informe, script
  reproducible y decisión confirmada en `docs/spikes/`; PRD actualizado. S6 pasó a la Etapa 5.
