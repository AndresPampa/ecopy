# HANDOFF — ecopy (métricas históricas del ecosistema Python)
> Leer esto primero antes de tocar nada.
> Last updated: 2026-11-07 · branch: `etapa-0-spikes` (SIN commits: todo el trabajo de la Etapa 0 está
> en el working tree) · `main` = `origin/main` (PR #1) · remoto `origin` = https://github.com/AndresPampa/ecopy.git

## Current State
- **PRD vigente** en `docs/prd.md`: 53 historias (49–53 = categorías y tags), seams de test acordados
  (CLI end-to-end → `sources` contrato → `store` inmutabilidad → `metrics` puros + Hypothesis →
  `site` snapshots), sección Taxonomía y decisiones de S1–S4 ya incorporadas (S5 todavía no).
- **Etapa 0 (spikes) en curso** en la rama `etapa-0-spikes` (`docs/ROADMAP.md`):
  - S1 ClickPy cobertura ✅ confirmado → datos desde 2016-01-22, vistas anuales desde 2017.
  - S2 versiones de Python ✅ → historia 5 confirmada (mensual).
  - S3 estrellas ✅ confirmado → `stargazers/history` existe; historia 17 confirmada.
  - S4 ECharts vs Plotly ✅ confirmado (2026-11-07) → ECharts 6 `common`, servido desde el sitio;
    PRD actualizado (Frontend + Further Notes).
  - S5 tamaño Parquet + backfill ✅ hecho, **decisión pendiente del usuario** (propuesta: alcanza
    el repo, sin R2; guardar serie diaria; backfill ≈ 10 MB, ~3 MB/año). El PRD NO refleja S5.
  - S6 Cloudflare Pages ⏳ (lo hace el usuario).
- **Sin commits en la rama.** Cambios pendientes: `.gitignore` (usuario agregó `categorias.md`; agente
  agregó `build/`), `README.md`, `docs/HANDOFF.md`, `docs/prd.md`, nuevos `docs/ROADMAP.md` y
  `docs/spikes/`. El usuario hace commit/push/PR al cerrar la etapa (una rama + commit + PR).
- **No hay código del producto todavía.** Tooling del agente local y fuera de git (`.claude/`,
  `.codex/`, `.agents/`, `skills/`, `openspec/`, `scripts/hooks|bash/`, `docs/workflows|guides|
  prompt_templates/`, `AGENTS*/CLAUDE*`, `brainstorming.md`, `categorias.md`, `build/`).

## Next Steps
- [ ] **Etapa 0 — Spikes** (rama `etapa-0-spikes`): slices en `docs/ROADMAP.md`, informes en
      `docs/spikes/`. S1–S4 hechos y confirmados (PRD actualizado). S5 hecho: **confirmar la
      decisión** de `docs/spikes/s5-parquet-backfill.md`; al confirmar, volcar al PRD (Datos:
      serie diaria, disposición por año/día, sin R2; Fuentes: hallazgos 1–3 del adaptador) y
      tildar S5 en ROADMAP. Falta S6 (Cloudflare Pages, usuario).
- [ ] **Usuario:** commit de la Etapa 0 en `etapa-0-spikes` (comandos y mensaje propuestos en la
      sesión del 2026-11-07) y PR cuando S5/S6 cierren.
- [ ] **Usuario (opcional):** borrar la rama `docs/project-setup` (local y remota), ya mergeada.
- [ ] Opcional: instalar `ruff`, `pytest`, `pre-commit` cuando arranque la Etapa 1 (hay `uv` 0.12.19,
      Python 3.14.4, node).
- [ ] Opcional: activar hooks de Claude Code copiando `.claude/settings.template.json` →
      `.claude/settings.json` (hoy los guards solo corren en Codex).

## Key Decisions & Why
- **Flujo simple, proyecto de una persona:** etapas en `docs/ROADMAP.md`; cada etapa = una rama
  `etapa-N-<tema>` + commit(s) + PR a `main`. **Sin issues ni OpenSpec** (CLI no instalado,
  `openspec/` ignorado por git, y su guía exige proposal/aprobación/verify/archive por change:
  demasiado peso para una persona). `to-issues` descartado por lo mismo.
- **Licencia MIT** (recomendada por simple y permisiva; aceptada por el usuario). Titular: `AndresPampa`.
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
- **Backfill desde 2016-01-22, vistas anuales desde 2017** (spike S1, confirmado por el usuario) vía **ClickPy** (agregados, usuario `play`, gratis);
  **BigQuery** solo como respaldo reproducible (cobra por bytes escaneados). Sin pedir permiso a
  ClickPy: el dato es público (PyPI/linehaul); se atribuye y se consulta con moderación.
- **Datos:** DuckDB + Parquet **append-only** particionado dentro del repo (`data/raw/` →
  `data/normalized/`; métricas se recalculan en cada build). Procedencia por fila
  (`source`, `acquisition=backfill|observed`, `captured_at`, `ingestion_run_id`). Correcciones de la
  fuente = archivo nuevo, nunca sobrescribir. Git LFS descartado; R2 como plan B.
- **Gráficos: ECharts 6 build `common`** (S4, confirmado): 195 KB brotli vs 324 KB Plotly basic,
  sin violaciones de CSP; versión fija servida desde el sitio con hash (`script-src 'self'`);
  renderer SVG; `full` solo si la vista anual pide treemap/heatmap.
- **Frontend Python-first:** Jinja2 (HTML) + ECharts (opciones generadas desde Pydantic) + SVG
  generado en Python para sparklines. Dash/Streamlit/Reflex/NiceGUI descartados (requieren
  servidor); PyScript descartado (peso). Diseño con skills `impeccable` + `dataviz`.
- **MVP:** vista anual, librerías + descargas, releases de Python, comparador simple, metodología,
  EN/ES. Estrellas de GitHub vía `stargazers/history` (S3). Trending y Seguridad → Fase 3. Ya no
  hacen falta snapshots diarios "irrecuperables": la historia se recupera; se guarda página 1 +
  `stargazers_count` por corrida.
- **Categorías (abordaje del usuario, `categorias.md` local e ignorado por git):** dominio →
  categoría, una categoría principal por librería + tags de vocabulario controlado (solo
  navegación). Detalle en PRD "Taxonomía"; lista fina se cierra en la Etapa 2.
- **Catálogo ~500:** unión del top 100 de cada año desde 2017 (evita sesgo de supervivencia) +
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
- **Consultas grandes a ClickPy devuelven resultados parciales sin error** (usuario `play`:
  `read_overflow_mode=break` a 10.000 M filas leídas, `result_overflow_mode=break` a 1.000 filas de
  resultado, `readonly=1`). Siempre verificar `X-ClickHouse-Summary` (`read_rows` vs
  `total_rows_to_read`) y < 1.000 filas; leer tablas grandes por rangos de `project` (filtrar por
  fecha no reduce lo leído). Ver `docs/spikes/s2-clickpy-versiones-python.md`.
- **Más trampas de ClickPy (S5):** `pypi_downloads_per_day` es SummingMergeTree con partes sin
  fusionar → hay filas duplicadas por (paquete, día): siempre `GROUP BY` + `sum(count)`. El
  resumen sale con el primer bloque (`result_bytes`=0) salvo `wait_end_of_query=1`. El límite de
  10 MB no corta fiable (lotes de ~13 MB llegaron completos): lotes ≤ 50 paquetes en modo array +
  cuadre contra sumas de control del servidor. Paginar 1 fila por (paquete, día) = 1.659 consultas:
  usar arrays (10 consultas). `python_minor` trae comas/barras: separadores de control y
  `split("\n")`, no `splitlines()`. Ver `docs/spikes/s5-parquet-backfill.md`.
- Ejecutar el launcher `skills/impeccable/scripts/impeccable` fue bloqueado por el clasificador de
  permisos (descarga un binario desde GitHub Releases, verificado por SHA-256). No se ejecutó;
  el skill funciona sin él leyendo PRODUCT.md/DESIGN.md. Requiere autorización del usuario.
- Nombres descartados: PyScope (PyPI), State of Python (JetBrains/PSF), pytonic (PyPI, GitHub,
  app iOS homónima; se lee como typo de "pythonic"), ecopython (permiso PSF).

- El commit `46bc2dd` quedó sin línea de asunto (el cuerpo del mensaje se aplanó en una sola
  línea). No se reescribe: ya está mergeado en `main`. Para mensajes multilínea usar
  `git commit -F archivo` o el editor, no `-m` con el texto pegado.

## Files & Pointers
- `docs/ROADMAP.md` — etapas y slices de la etapa en curso.
- `docs/spikes/` — informe (`sN-*.md`) + script reproducible (`sN_*.py`) por spike: S1 cobertura,
  S2 versiones de Python, S3 estrellas, S4 ECharts vs Plotly, S5 Parquet + backfill.
- `categorias.md` (raíz, ignorado por git) — abordaje de categorías del usuario; ya volcado al PRD.
- `build/spikes/s4/`, `build/spikes/s5/` (ignorados) — salidas de prototipos; se regeneran con su script.
- `docs/prd.md` — PRD vigente (fuente funcional para issues e implementación).
- `brainstorming.md` — documento funcional original (desactualizado; ignorado por git).
- `.gitignore` — qué tooling queda local.
- `skills/impeccable/` — skill de diseño frontend (v4.8.0, commit `c3bb418`); notice en
  `skills/THIRD-PARTY-NOTICES.md`. `scripts/data/font-index.json` pesa 1.1 MB (choca con el
  límite de 1024 KB del pre-commit si se adopta).
- Memoria persistente del agente: `ecopython-brainstorm-decisions`, `user-owns-git-operations`.

## Resume Setup
- Checks del toolkit: `scripts/bash/check_skill_symlinks.sh`, `check_hook_parity.sh`,
  `check_agent_parity.sh`; tests: `python3 scripts/hooks/test_<nombre>.py` (sin pytest).
- Spikes: scripts con dependencias inline (PEP 723), `uv run docs/spikes/<script>.py`. ClickPy:
  `https://sql-clickhouse.clickhouse.com/?user=play` (ver límites en Failed Approaches). S4 usa
  Google Chrome headless (`/usr/bin/google-chrome`).
- Git: el agente NUNCA hace add/commit/push/PR; entrega comandos, mensaje (`git commit -F`) y texto de PR.
- Suggested skills: para la Etapa 1+ `tdd`, `codebase-design`;
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

### 2026-11-06 — README reescrito para ecopy
`README.md` ahora describe ecopy (estado, MVP, arquitectura, roadmap, fuentes); antes era el del template.
Se agregó `LICENSE` (MIT) y la sección Licencia al README.

### 2026-11-06 — Primer PR mergeado
El usuario creó `main` (commit inicial 3432f25) y mergeó el PR #1 (`docs/project-setup`: README,
LICENSE MIT, ajustes al handoff). Local `main` = `origin/main` (aa92dfe).

### 2026-11-06 — Etapas definidas; flujo rama-por-etapa
Usuario pidió simplificar. Se revisó `openspec/` (vacío, CLI no instalado, ignorado por git) y se
descartó OpenSpec e issues. `docs/ROADMAP.md`: Etapas 0–5 + post-MVP; Etapa 0 (spikes) en slices S1–S6.

### 2026-11-06 — Spike S1 (ClickPy cobertura)
Endpoint que funciona: `https://sql-clickhouse.clickhouse.com/?user=play` (el host
`clickpy-clickhouse...` falla TLS). Datos desde 2016-01-22; huecos 2016-03-06→05-21 y
2019-04-26/27; ventana degradada 2018-07-13→26; salto ×3 en volumen el 2018-07-27, uniforme en
cuota. Consultas por día con `uniqExact(project)` sobre todo el rango exceden el límite de memoria
(18,6 GiB) de la instancia pública: usar `count()`.

### 2026-11-06 — Spike S2 (versiones de Python) y límites de ClickPy
Hay desglose por `python_minor` desde 2016, completo (cuadra 100 % con la tabla diaria) leído en 4
rangos de `project`. Historia 5 confirmada (mensual). Descubierto que el usuario `play` trunca en
silencio lecturas > 10.000 M filas y resultados > 1.000 filas; guard agregado a ambos scripts.

### 2026-11-06 — Spike S3 (estrellas) y pedido de categorías
`GET /repos/{o}/{r}/stargazers/history` EXISTE (documentado): semanas con días, 30 por página,
neto, cuadra exacto con `stargazers_count` (uv: 91.713). `starred_at` ya exige auth (401). Mapeo
paquete→repo de ClickPy (`pypi.project_to_repo_name`) incompleto/desactualizado. Decisión propuesta
en `docs/spikes/s3-github-estrellas.md`, pendiente. El usuario pidió librerías por categorías (ML,
web, scraping…): ya estaban en el PRD (historias 2, 12, 39), pero falta definir la taxonomía y si
una librería tiene una o varias categorías.

### 2026-11-07 — S3 confirmado; taxonomía de categorías al PRD
Usuario confirmó S3. Leído `categorias.md` (local, ignorado): dominios → categorías + tags. PRD:
sección Taxonomía, historias 49–53, 12/17/38/39 ajustadas. Observaciones para el catálogo
(verificadas en ClickPy, descargas 2025): sin descargas en PyPI `tkinter`, `pydoc` (stdlib), `rclpy`
(ROS), `socket.io` (→ `python-socketio`), `opentelemetry` (→ `opentelemetry-api`/`-sdk`); `whisper`
es otro paquete (→ `openai-whisper`); `mypyc` viene dentro de `mypy`. `celery` aparece en dos
categorías; `scipy`, `pyarrow`, `dask` tienen ubicación discutible.

### 2026-11-07 — Spike S4 (ECharts vs Plotly)
Prototipo ranking + ficha con datos reales, CSP estricta en Chrome headless. ECharts 6.1.0
`common`: 195 KB brotli, sin violaciones. Plotly.js 4.1.2 basic: 324 KB, inyecta `<style>` inline
(se rompe con CSP salvo que se enlace `dist/plotly.css`). ECharts `simple` no trae title/tooltip/
dataZoom. `build/` agregado a `.gitignore` (salidas del prototipo).

### 2026-11-07 — Cierre de sesión
Handoff y README actualizados para retomar. Pendiente: confirmación de S4, luego S5.

### 2026-11-07 — S4 confirmado; spike S5 (Parquet + backfill)
Resume sin drift (rama y working tree coinciden con el handoff). Usuario confirmó S4 → PRD
(Frontend, Further Notes), ROADMAP e informe actualizados. S5: catálogo de prueba de 500 (la unión
del top 100 anual 2017–2026 da solo 213); 1,66 M filas diarias → 7,3 MB Parquet (zstd, por año),
mensual 0,3 MB, Python por paquete 2,65 MB; 64 consultas, ~37 s en modo array. Ingesta diaria
~3 MB/año; ≤ 125 MB a 10 años en el peor supuesto → alcanza el repo. Descubiertos duplicados sin
fusionar, resumen temprano sin `wait_end_of_query` y límite de 10 MB no fiable. Decisión pendiente.
