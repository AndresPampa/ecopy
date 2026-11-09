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
- 🚧 **Etapa 1 — Tracer bullet (local):** un paquete, de ClickPy a una página generada y servida
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

## Etapa en curso — Etapa 1: Tracer bullet

**Rama:** `etapa-1-tracer-bullet`

**Objetivo:** un paquete, de ClickPy a una página HTML generada en `build/` y servida en
localhost, atravesando `sources → store → metrics → site → cli`. Todo corre en local con `uv`;
GitHub Actions y Cloudflare Pages quedan para la Etapa 5 (decisión del usuario, 2026-11-07:
publicar recién con un primer MVP).

**Diseño:** `docs/design/etapa-1-tracer-bullet.md` (interfaces, seams y tests por módulo;
aprobado 2026-11-09).

**Slices** (TDD, en orden):
- [x] **1 — Esqueleto:** `pyproject.toml` (uv), `src/ecopy/`, `ruff` + `pytest` + `hypothesis`.
- [x] **2 — `sources.clickpy`:** fixtures grabadas de `fastapi` + tests de contrato (truncado, cuadre).
- [x] **3 — `store`:** append-only, lectura con corrección, inmutabilidad sobre `tmp_path`.
- [ ] **4 — `metrics.library_view`:** unitarios + propiedades con Hypothesis.
- [ ] **5 — `site.render_site`:** Jinja2, ECharts `common` vendorizado con hash, `_headers`, snapshots.
- [ ] **6 — `cli`:** `ingest`, `build`, `serve` + humo end-to-end; corrida real y CSP en Chrome headless.

## Shipped

- ✅ **Etapa 0 — Spikes de validación** (PR #2, 2026-11-07): S1–S5 con informe, script
  reproducible y decisión confirmada en `docs/spikes/`; PRD actualizado. S6 pasó a la Etapa 5.
