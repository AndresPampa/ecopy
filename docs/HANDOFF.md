# HANDOFF — ecopy (métricas históricas del ecosistema Python)
> Leer esto primero antes de tocar nada.
> Last updated: 2026-11-06 · branch: master (sin commits todavía) · remoto `origin` = https://github.com/AndresPampa/ecopy.git (vacío)

## Current State
- **Brainstorming cerrado** (skill `grill-me`); decisiones en "Key Decisions" abajo.
  `brainstorming.md` NO se modificó y está desactualizado (PyScope / FastAPI+Postgres / Dash vs React).
- **PRD cerrado** en `docs/prd.md` (2026-11-06): 48 historias de usuario, módulos, seams de test
  acordados con el usuario (CLI end-to-end → `sources` contrato → `store` inmutabilidad →
  `metrics` puros + Hypothesis → `site` snapshots). Es la referencia funcional vigente.
- **No hay código del producto todavía.** El repo es el template de tooling Claude Code + Codex.
- **Tooling local, fuera de git:** `.gitignore` ignora `.claude/`, `.codex/`, `.agents/`, `skills/`,
  `openspec/`, pre-commit config, `AGENTS*.md`/`CLAUDE*.md`, `scripts/hooks/`, `scripts/bash/`,
  `docs/workflows/`, `docs/prompt_templates/`, `docs/guides/`, `docs/ROADMAP.template.md` y
  también `brainstorming.md`. Git solo ve `.gitignore`, `README.md` y `docs/` (HANDOFF.md, prd.md).
  Rama `master` sin commits. Remoto `origin` configurado (repo público vacío en GitHub).
- Todos los checks del toolkit en verde (paridad de agentes/hooks, skill-symlinks, 5 tests de hooks).

## Next Steps
- [ ] **Usuario:** primer commit + push (y, si quiere, renombrar `master` → `main` antes del push).
- [ ] Partir el PRD en issues con `/to-issues` (tracer-bullet). El repo ya existe, pero `gh` no está
      instalado → archivos locales (p. ej. `docs/issues/`) o instalar `gh`; la creación de issues en
      GitHub la decide/hace el usuario.
- [ ] Reescribir `README.md` para ecopy (hoy describe el template).
- [ ] Fase 0 (spikes de validación, ver "Further Notes" del PRD): cobertura de años y calidad antigua
      en ClickPy; si ClickPy tiene desglose por versión de Python; fuente de histórico de estrellas
      (probablemente NO existe `GET /repos/{o}/{r}/stargazers/history` — no verificado; alternativa:
      `starred_at` del listado de stargazers, con límites de paginación en repos grandes);
      peso real de ECharts vs Plotly en un prototipo de ranking + ficha; tamaño real del Parquet.
- [ ] Crear el proyecto en Cloudflare Pages y confirmar que `ecopy.pages.dev` está libre.
- [ ] Opcional: instalar `gh`, `openspec`, `ruff`, `pytest`, `pre-commit` (no están instalados;
      hay `uv` 0.12.19, Python 3.14.4, node).
- [ ] Opcional: activar hooks de Claude Code copiando `.claude/settings.template.json` →
      `.claude/settings.json` (hoy los guards solo corren en Codex).

## Key Decisions & Why
- **Git lo opera el usuario:** todos los `git add`, `commit`, `push` y PRs los hace el usuario. El agente
  solo prepara cambios en el working tree y sugiere comandos/mensajes; nunca los ejecuta.
- **Nombre: ecopy**, subtítulo "the Python ecosystem, year by year". PyScope está tomado en PyPI;
  "State of Python" es el informe de JetBrains/PSF; "ecopython" exige permiso escrito de la PSF
  (política de marca) y el usuario no quiere burocracia. PyPI `ecopy` (librería de ecología
  abandonada) no importa: no publicamos en PyPI. `github.com/ecopy` tomado → repo bajo la cuenta del usuario.
- **Sitio pre-generado, presupuesto cero:** GitHub Actions (cron diario, repo público) → ingesta
  Python → build → Cloudflare Pages (`ecopy.pages.dev`, sin dominio pago). Datos cambian 1×/día y
  todo es de lectura → sin servidor: costo cero, CDN, SEO, menos superficie de ataque.
  FastAPI solo para una futura API pública; Supabase para Fase 4 (auth/encuestas) — su free tier
  de 500 MB no alcanza para el histórico diario.
- **Backfill desde 2018** (antes si es gratis) vía **ClickPy** (agregados, usuario `play`, gratis);
  **BigQuery** solo como respaldo reproducible (cobra por bytes escaneados). Sin pedir permiso a
  ClickPy: el dato es público (PyPI/linehaul); se atribuye y se consulta con moderación.
- **Datos:** DuckDB + Parquet **append-only** particionado dentro del repo (`data/raw/` →
  `data/normalized/`; métricas se recalculan en cada build). Procedencia por fila
  (`source`, `acquisition=backfill|observed`, `captured_at`, `ingestion_run_id`). Correcciones de la
  fuente = archivo nuevo, nunca sobrescribir. Git LFS descartado; R2 como plan B.
- **Frontend Python-first:** Jinja2 (HTML) + ECharts (opciones generadas desde Pydantic) + SVG
  generado en Python para sparklines. Dash/Streamlit/Reflex/NiceGUI descartados (requieren
  servidor); PyScript descartado (peso). Diseño con skills `impeccable` + `dataviz`.
- **MVP:** vista anual, librerías + descargas, releases de Python, comparador simple, metodología,
  EN/ES. Estrellas de GitHub si el endpoint se verifica. Trending y Seguridad → Fase 3, pero se
  guardan snapshots diarios de estrellas desde el día 1 (no se pueden recuperar después).
- **Catálogo ~500:** unión del top 100 de cada año desde 2018 (evita sesgo de supervivencia) +
  lista curada por categoría en YAML. Renombres enlazados, nunca sumados.
- **Vista anual:** cuota por categoría (neutraliza inflación por CI), movers, recién llegados,
  adopción de versiones de Python, línea de tiempo del lenguaje, volumen total con advertencia.
  Año calendario UTC; año en curso = YTD vs mismo período; rankings anuales congelados con versión
  metodológica; ningún puntaje combinado.
- **Módulos:** `sources`, `store`, `catalog`, `metrics`, `site`, `cli`; `site` nunca toca `store`.
  Tests: contrato (fixtures + `httpx.MockTransport`), inmutabilidad, propiedades (Hypothesis),
  unitarios puros, snapshots, humo end-to-end.
- **Seguridad:** nunca persistir usuarios de GitHub (solo conteos); Jinja2 autoescape, sin `|safe`
  en campos externos, sin Markdown externo, solo URLs https, CSP estricta vía `_headers`; Actions
  fijadas por SHA, permisos mínimos por job, sin `pull_request_target`; si la validación falla se
  publica el día anterior con estado "Actualización fallida".
- **Tooling fuera de git** por decisión del usuario. `check_skill_symlinks.sh` acepta lo ignorado
  en `.gitignore` como local a propósito, pero sigue fallando si algo no está trackeado NI ignorado.

## Failed Approaches
- Ejecutar el launcher `skills/impeccable/scripts/impeccable` fue bloqueado por el clasificador de
  permisos (descarga un binario desde GitHub Releases, verificado por SHA-256). No se ejecutó;
  el skill funciona sin él leyendo PRODUCT.md/DESIGN.md. Requiere autorización del usuario.
- Nombres descartados: PyScope (PyPI), State of Python (JetBrains/PSF), pytonic (PyPI, GitHub,
  app iOS homónima; se lee como typo de "pythonic"), ecopython (permiso PSF).

## Files & Pointers
- `docs/prd.md` — PRD vigente (fuente funcional para issues e implementación).
- `brainstorming.md` — documento funcional original (desactualizado; ignorado por git).
- `.gitignore` — qué tooling queda local.
- `scripts/bash/check_skill_symlinks.sh` (`is_tracked`) y `scripts/hooks/test_skill_symlinks.py`
  (casos "ignorado") — cambio de esta sesión.
- `skills/impeccable/` — skill de diseño frontend (v4.8.0, commit `c3bb418`); notice en
  `skills/THIRD-PARTY-NOTICES.md`. `scripts/data/font-index.json` pesa 1.1 MB (choca con el
  límite de 1024 KB del pre-commit si se adopta).
- Memoria persistente del agente: `ecopython-brainstorm-decisions` (mismas decisiones).

## Resume Setup
- Checks del toolkit: `scripts/bash/check_skill_symlinks.sh`, `check_hook_parity.sh`,
  `check_agent_parity.sh`; tests: `python3 scripts/hooks/test_<nombre>.py` (sin pytest).
- Suggested skills: `to-issues` (siguiente paso), luego `tdd`, `codebase-design`;
  para diseño `impeccable` + `dataviz`; `handoff-doc` al cerrar.

---

## Session Log
### 2026-11-05 — Inventario de herramientas, skill impeccable, brainstorming
Inventario de skills/agentes/hooks/OpenSpec del template. Se agregó `skills/impeccable` (fuente
única + symlinks en ambas farms, LICENSE/NOTICE, entrada en THIRD-PARTY-NOTICES). Sesión
`grill-me` de 10 preguntas sobre `brainstorming.md`: arquitectura estática de costo cero, backfill,
almacenamiento, frontend, alcance del MVP, catálogo, indicadores, módulos, seguridad, nombre.
Todo el tooling se movió a `.gitignore`.

### 2026-11-06 — Nombre ecopy, ClickPy sin permiso, checks compatibles con .gitignore
Nombre cambiado a ecopy (`ecopy.pages.dev`) para evitar permiso de la PSF; ClickPy se usa con
atribución. `check_skill_symlinks.sh` ahora acepta rutas ignoradas por `.gitignore` (TDD: 3 casos
nuevos en `test_skill_symlinks.py`, rojo → verde, 23/23). Todos los checks y tests del toolkit en verde.

### 2026-11-06 — PRD cerrado
Resume del handoff (drift detectado: `brainstorming.md` está en `.gitignore`, el handoff decía que
git lo veía; corregido). PRD escrito con `/to-prd` desde "Key Decisions" → `docs/prd.md`, en español;
seams de test confirmados por el usuario. Se marcó como dudoso el endpoint de historial de estrellas.

### 2026-11-06 — Remoto configurado; git lo opera el usuario
Usuario creó https://github.com/AndresPampa/ecopy (vacío). Se agregó como `origin`. Decisión: el
agente nunca hace add/commit/push/PR.
