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
- ✅ **Etapa 3 — Vista anual:** cuota por categoría, movers, recién llegados, adopción de versiones,
  línea de tiempo, volumen total con advertencia, YTD y rankings congelados.
- ✅ **Etapa 4 — Base visual, librerías y comparador:** cabecera, navegación, portada y sistema de
  estilos (`impeccable` + `dataviz`); fichas con series y sparklines, comparador, releases de
  Python, estrellas, páginas de dominio/categoría y filtro por tags.
- ✅ **Ajustes visuales de la Etapa 4:** selector de tema, créditos, alineación y comparador vacío.
- 🚧 **Etapa 5 — Publicación del MVP:** EN/ES completo, metodología, CSP/`_headers`, auditoría de
  accesibilidad y pulido final; GitHub Actions (cron diario) y despliegue en Cloudflare
  Pages, incluido S6 (crear el proyecto y confirmar `ecopy.pages.dev`, lo hace el usuario).
- 📋 **Después del MVP:** Trending y Seguridad (Fase 3); cuentas y encuestas (Fase 4).

## Etapa en curso — Publicación del MVP

**Rama:** `etapa-5-publicacion`, mergeada en PR #9 (2026-11-10); solo falta el ítem 6. Decisiones aprobadas (2026-11-10): `/` → `/en/`,
estrellas semanales, commits del bot directo a `main`, sin el launcher de `impeccable`.

- [x] 1. Entrada y SEO: `_redirects`, 404 EN/ES, favicon, descripción, canonical, hreflang, sitemap y
      robots.
- [x] 2. Página de metodología EN/ES.
- [x] 3. Auditoría de accesibilidad y pulido (sparklines y tabla de 2026 a 390 px).
- [x] 4. Workflows de GitHub Actions fijados por SHA: ingesta diaria, estrellas semanales, deploy y CI.
- [x] 5. Auditoría de seguridad con `security-audit` (Cloudflare), perfil `standard`: 1 hallazgo bajo
      confirmado y 3 que necesitan validación; informe en `~/security-audit-skill/ecopy/run-1/`.
- [x] 5b. Arreglos de la auditoría: corrida `failed` ante cualquier error de ingesta y errores de
      formato de ClickPy como `SourceError`; `update.yml` publica solo desde `main`, empuja solo el
      commit de datos y da el token solo al push; `retry-after` con tope y plazo para `stars`.
      `python_minor` codificado quedó para después: ClickPy no tiene separadores en ese campo (0
      filas, 2026-11-10) y codificarlo cambiaría claves ya guardadas.
- [ ] 6. **Usuario:** S6 (proyecto en Cloudflare Pages y secretos) y primer deploy.

## Shipped

- ✅ **Ajustes visuales de la Etapa 4** (PR #8, 2026-11-10): selector de tema Pythonista/Pythoneer,
  créditos en el pie, cabecera alineada y comparador vacío sin eje suelto.
- ✅ **Etapa 4 — Base visual, librerías y comparador local** (PR #6 y #7, 2026-11-10): dirección
  Estratos, fichas ampliadas, listados con sparklines y filtro por tags, dominios y categorías,
  comparador, releases de Python y estrellas de 458 repos con `ecopy stars`. Diseño en
  `docs/design/etapa-4-librerias-y-comparador.md`.
- ✅ **Etapa 3 — Vista anual local** (PR #5, 2026-11-09): páginas por año EN/ES con cuotas, movers,
  recién llegados, adopción de Python, línea de tiempo y volumen; años cerrados congelados con
  `ecopy freeze`. Diseño en `docs/design/etapa-3-vista-anual.md`.
- ✅ **Etapa 2 — Datos completos local** (PR #4, 2026-11-09): catálogo de 500, backfill desde 2016,
  totales de PyPI, versiones de Python, ingesta con reobservación, validación y aviso de fallo.
  Diseño en `docs/design/etapa-2-datos-completos.md`.
- ✅ **Etapa 1 — Tracer bullet local** (PR #3, 2026-11-09): `ingest → build → serve` de punta a
  punta con `fastapi`; ficha EN/ES con ECharts y CSP estricta. Diseño en
  `docs/design/etapa-1-tracer-bullet.md`.
- ✅ **Etapa 0 — Spikes de validación** (PR #2, 2026-11-07): S1–S5 con informe, script
  reproducible y decisión confirmada en `docs/spikes/`; PRD actualizado. S6 pasó a la Etapa 5.
