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
- ✅ **Etapa 2 — Datos completos:** (incluye cerrar la taxonomía de categorías y tags en el YAML) backfill desde 2016-01-22 (vistas desde 2017), catálogo ~500 (YAML + top 100 anual,
  renombres), procedencia por fila, ingesta diaria y validación con "Actualización fallida".
- 📋 **Etapa 3 — Vista anual:** cuota por categoría, movers, recién llegados, adopción de versiones,
  línea de tiempo, volumen total con advertencia, YTD y rankings congelados.
- 📋 **Etapa 4 — Librerías y comparador:** fichas con series y sparklines, comparador, releases de
  Python, estrellas, páginas de dominio/categoría y filtro por tags.
- 📋 **Etapa 5 — Publicación del MVP:** EN/ES completo, metodología, CSP/`_headers`, accesibilidad
  y diseño (`impeccable` + `dataviz`); GitHub Actions (cron diario) y despliegue en Cloudflare
  Pages, incluido S6 (crear el proyecto y confirmar `ecopy.pages.dev`, lo hace el usuario).
- 📋 **Después del MVP:** Trending y Seguridad (Fase 3); cuentas y encuestas (Fase 4).

## Próxima etapa — Etapa 3: Vista anual

**Rama sugerida:** `etapa-3-vista-anual`

**Objetivo:** una página por año desde 2017, EN/ES, con cuotas, movers, recién llegados, adopción
de Python, línea de tiempo y volumen; YTD y años cerrados congelados. Todo en local.

**Diseño:** `docs/design/etapa-3-vista-anual.md` (aprobado 2026-11-09).

**Slices (TDD):**

- [x] 1. Releases de Python y top 100 en `catalog`.
- [x] 2. `year_view`: cuotas, ventanas y volumen.
- [x] 3. Movers y recién llegados.
- [x] 4. Adopción de Python y línea de tiempo.
- [x] 5. Congelado: `ecopy freeze` y `build` leyendo lo congelado.
- [x] 6. `site`: páginas por año EN/ES y gráficos.
- [ ] 7. Corrida real hecha sobre una copia; falta `ecopy freeze` en `data/`, tras la revisión del catálogo.

**Heredado de la Etapa 2:**

- [ ] Revisar `catalog/libraries.yaml` (usuario): tiene que ser antes de congelar los años cerrados.
- [ ] Correr `ecopy ingest` en un día posterior y mirar `revised_rows` en `data/runs/`.

## Shipped

- ✅ **Etapa 2 — Datos completos local** (PR #4, 2026-11-09): catálogo de 500, backfill desde 2016,
  totales de PyPI, versiones de Python, ingesta con reobservación, validación y aviso de fallo.
  Diseño en `docs/design/etapa-2-datos-completos.md`.
- ✅ **Etapa 1 — Tracer bullet local** (PR #3, 2026-11-09): `ingest → build → serve` de punta a
  punta con `fastapi`; ficha EN/ES con ECharts y CSP estricta. Diseño en
  `docs/design/etapa-1-tracer-bullet.md`.
- ✅ **Etapa 0 — Spikes de validación** (PR #2, 2026-11-07): S1–S5 con informe, script
  reproducible y decisión confirmada en `docs/spikes/`; PRD actualizado. S6 pasó a la Etapa 5.
