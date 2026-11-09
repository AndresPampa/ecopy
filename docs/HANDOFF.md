# HANDOFF — ecopy (métricas históricas del ecosistema Python)
> Leer esto primero antes de tocar nada.
> Last updated: 2026-11-09 · branch: `etapa-4-librerias-y-comparador` (desde `main` = `ea14545`), con
> toda la Etapa 4 sin commit, a la espera de que el usuario la revise y la commitee · remoto `origin` =
> https://github.com/AndresPampa/ecopy.git

## Current State
- **Etapa 0 (spikes) mergeada** (PR #2): S1–S5 confirmados, informes en `docs/spikes/`.
- **Etapa 1 (tracer bullet, LOCAL) mergeada** (PR #3): los 6 slices están hechos, 73 tests en verde.
  `ecopy ingest → build → serve` funciona de punta a punta con datos reales de `fastapi` (2.891
  días, `data/` = 120 KB): página EN/ES con tabla anual, tabla mensual y gráfico ECharts,
  servida con la CSP real. Sin violaciones en Chrome headless (con control positivo), tooltip y
  móvil verificados. Diseño: `docs/design/etapa-1-tracer-bullet.md`.
- **Etapa 3 (vista anual, LOCAL) mergeada** (PR #5): 252 tests y 54 mutaciones con arnés
  corregido, sin violaciones de CSP en Chrome. `ecopy freeze` ya corrió en `data/` (2017–2025,
  metodología 1, sin commit) y `ecopy build` completo funciona: 500 fichas y 10 años en 9 s.
- **Etapa 4 implementada en local, sin commit:** base visual (dirección Estratos), fichas ampliadas,
  catálogo con sparklines y filtro por tags, dominios y categorías, comparador, releases y `ecopy
  stars`. 340 tests, 41 mutaciones detectadas, Chrome sin violaciones de CSP (con control positivo).
  Build real: 500 fichas y 10 años en 18 s. **Falta la corrida real de estrellas:** sin token solo
  se probó `astral-sh/uv`.
- **Etapa 2 (datos completos, LOCAL) mergeada** (PR #4). Corrida
  real: 500 paquetes desde 2016-01-22 (1.708.804 filas), totales de PyPI (3.866 días), versiones de
  Python (2.322 filas), `data/` = 7,4 MB, 42 s; reobservación sin archivos nuevos; 1.000 páginas en
  9 s. Diseño: `docs/design/etapa-2-datos-completos.md`. Quedan abiertos los slices 7 y 8.
- **PRD vigente** en `docs/prd.md` con las decisiones de S1–S5 y del diseño de la Etapa 1.
- **GitHub Actions y Cloudflare Pages (S6) quedan para la Etapa 5** (decisión del usuario).
- Tooling del agente local y fuera de git (`.claude/`, `.codex/`, `.agents/`, `skills/`,
  `openspec/`, `scripts/hooks|bash/`, `docs/workflows|guides|prompt_templates/`, `AGENTS*/CLAUDE*`,
  `brainstorming.md`, `categorias.md`, `build/`).

## Next Steps
- [ ] **Usuario:** revisar por excepción `catalog/libraries.yaml` (7 en `other`, tags nuevos) y
      `catalog/repos.yaml` (lo que marca `docs/spikes/s8-repos-y-tags.md`). Si cambia una categoría:
      borrar `data/frozen/`, volver a correr `uv run ecopy freeze`. `repo` y tags no lo invalidan.
- [ ] **Usuario:** commit de la Etapa 4, luego `data/frozen/` tras la revisión, y PR.
- [ ] **Usuario (corrida real de estrellas):** token *fine-grained*, solo lectura de repos públicos,
      en `GITHUB_TOKEN`: `read -rs GITHUB_TOKEN && export GITHUB_TOKEN`, y 3 veces
      `uv run ecopy stars --budget 4000` (~9.500 consultas, ~2,6 h, se reanuda sola). Después
      `uv run ecopy build`, y corregir en `repos.yaml` los repos que informe como movidos o fallidos.
- [ ] **Usuario:** borrar las ramas remotas ya mergeadas; las locales ya están borradas:
      `git push origin --delete etapa-0-spikes etapa-1-tracer-bullet etapa-2-datos-completos etapa-3-vista-anual`.
- [ ] **Pendiente de la Etapa 2:** correr `uv run ecopy ingest` desde el 2026-11-10 y mirar `revised_rows`
      en `data/runs/`: el mismo día da 0 nuevas y 0 corregidas, porque llega hasta ayer (UTC).
- [ ] **Investigar la caída desde 2026-08-25** (−36 % de un día para el otro, recuperación lenta,
      algunos paquetes ×0,12). Ya está marcada como discontinuidad: si se explica, revisar esa marca.
- [ ] **Usuario (Etapa 5, con el primer MVP):** S6 — crear el proyecto en Cloudflare Pages y
      confirmar `ecopy.pages.dev`; recién ahí entra GitHub Actions.
- [ ] **Etapa 5:** las sparklines se encogen en 390 px (`/library/`); revisar en la auditoría y el pulido.
- [ ] Opcional: activar hooks de Claude Code copiando `.claude/settings.template.json` →
      `.claude/settings.json` (hoy los guards solo corren en Codex).

## Key Decisions & Why
- **Flujo simple, proyecto de una persona:** etapas en `docs/ROADMAP.md`; cada etapa = una rama
  `etapa-N-<tema>` + commit(s) + PR a `main`. **Sin issues ni OpenSpec** (CLI no instalado,
  `openspec/` ignorado por git, y su guía exige proposal/aprobación/verify/archive por change:
  demasiado peso para una persona). `to-issues` descartado por lo mismo.
- **Base visual en la Etapa 4** (decisión del usuario, 2026-11-09): cabecera, navegación, portada y
  sistema de estilos van primero, porque las páginas nuevas de esa etapa se apoyarían en una base que
  después habría que rehacer. La auditoría de accesibilidad y el pulido final siguen en la Etapa 5.
- **Local primero:** Etapas 1–4 se construyen y prueban en local (`build/` + localhost). GitHub
  Actions y Cloudflare Pages entran recién en la Etapa 5, con un primer MVP (decisión del usuario,
  2026-11-07). La arquitectura del PRD no cambia, solo el orden.
- **Diseño de la Etapa 1 (aprobado 2026-11-09):** `normalized` es una vista (dedup + la
  corrección más reciente gana), no capa física, hasta que haya una segunda fuente; la
  procedencia la sella `store` desde un `Run` que crea `cli` (`sources` no sabe si es backfill);
  `data/` se versiona desde ya; partición única `raw/<fuente>/<dataset>/year=YYYY/<run_id>.parquet`.
  Detalle y razones en `docs/design/etapa-1-tracer-bullet.md`; PRD actualizado.
- **pre-commit del producto versionado** (decisión del usuario, 2026-11-09): hooks locales con
  `uv run` (ruff check --fix, ruff format, pytest), así usan las versiones de `uv.lock`; solo
  sobre `src/` y `tests/`. El template del toolkit sigue ignorado.
- **Ficha (Etapa 1):** un mes sin datos es `None` (corte en la línea, no cero); el mes en curso va
  en un tramo punteado aparte; `build` usa `as_of` = último día con datos (no depende del reloj).
  ECharts 6.1.0 `common` vendorizado en `src/ecopy/site/static/vendor/` con SHA-256 fijo y su
  LICENSE/NOTICE (Apache-2.0).
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

- **Diseño de la Etapa 2 (aprobado 2026-11-09, las 10 recomendaciones):** reobservar 7 días y
  escribir solo cambios; validar antes de escribir y, si falla, reconstruir con aviso (una corrida
  mala ganaría al leer); calidad como calendario en código (un hueco no tiene filas donde marcar);
  top 100 como archivo revisado; versiones solo con meses cerrados; módulo `pipeline`, sin comando
  `backfill`. Razones y evidencia en `docs/design/etapa-2-datos-completos.md`.

- **Diseño de la Etapa 4 (aprobado 2026-11-09, 9 decisiones):** dirección Estratos, mes en curso como
  franja (sin proyectar: con 3 días erra 31 % en p90), sparklines y comparador en cuota de PyPI (la
  correlación entre paquetes baja de 0,96 a 0,05), `repos.yaml` aparte, estrellas fuera de `ingest`.
  Categoría `other` para lo dudoso, pedida por el usuario. Razones: `docs/design/etapa-4-*.md`.

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

- El commit `0c00df2` (ya en `main` por PR #3) tiene como asunto una ruta de archivo: se usó `-m`
  con la ruta en lugar de `-F`. No se reescribe. Mismo cuidado que el caso siguiente.
- El commit `46bc2dd` quedó sin línea de asunto (el cuerpo del mensaje se aplanó en una sola
  línea). No se reescribe: ya está mergeado en `main`. Para mensajes multilínea usar
  `git commit -F archivo` o el editor, no `-m` con el texto pegado.

- **pre-commit pasa los archivos por nombre y ruff ignora `extend-exclude`**: la primera corrida
  reformateó los scripts de `docs/spikes/` (restaurados con `git restore`). Por eso
  `force-exclude = true` en ruff y `files: ^(src|tests)/` en `.pre-commit-config.yaml`.

- **El replay de fixtures no ejecuta SQL:** cambiar `sum(count)` por `max(count)` no rompe los
  tests de contrato. Lo atrapa en producción el cuadre (`ChecksumMismatch`, verificado contra
  ClickPy real con 21 filas duplicadas). Al cambiar consultas: regrabar con
  `uv run python tests/fixtures/clickpy/record.py` y probar contra ClickPy real.

- **Un test de humo no prueba seguridad por sí solo:** un nombre con `/` no ejercitaba el caso de
  un proyecto llamado exactamente `..`; lo reveló una mutación. Probar mutaciones en defensas.

- **Mutaciones con arnés roto:** en una copia, `test_version_command` falla si `.venv/bin` no está
  en el `PATH`, y con `-x` todas las mutaciones salían "rojas" sin probar nada. Las 24 reportadas
  en la Etapa 2 no eran válidas; al repetirlas sobrevivían 2. Siempre exigir verde sin mutar.

- **Dos conclusiones de spikes que no se sostienen (S7):** "no hay huecos propios de un paquete"
  (S1, con 5 paquetes): 369 de 500 tienen días sin filas, y no son huecos de la fuente. "La
  diferencia entre versiones y total es carga en vivo" (S2): aparece en meses cerrados.

- **`pkill -f '<patrón>'` desde el mismo Bash mata esa shell** (el patrón aparece en su propia línea
  de comandos). Guardar el PID del proceso y usar `kill $PID`.

- **GitHub sin token comparte 60 consultas/h por IP:** con la muestra de S8 se agotaron y `ecopy stars`
  se detuvo bien con `rate_limited`. Para probar, esperar al `reset` que da `/rate_limit`, que no consume.

- **En `library.html`, una macro no puede llamarse `status`:** tapa la variable `status` del
  contexto. Por eso es `period_status`.

## Files & Pointers
- `docs/ROADMAP.md` — etapas y slices de la etapa en curso.
- `docs/design/etapa-1-tracer-bullet.md` — interfaces, seams y tests de la Etapa 1.
- `docs/design/etapa-2-datos-completos.md` — diseño y evidencia de la Etapa 2.
- `docs/design/etapa-3-vista-anual.md` — diseño y evidencia de la Etapa 3.
- `docs/design/etapa-4-librerias-y-comparador.md` — diseño y evidencia de la Etapa 4.
- `DESIGN.md`, `PRODUCT.md` — sistema visual y contexto para `impeccable`.
- `build/preview-etapa-4/` (ignorado) — vistas previas de las tres direcciones visuales.
- `data/frozen/year=YYYY/methodology=N.json` — años cerrados congelados (`ecopy freeze`).
- `catalog/` — `taxonomy.yaml` (40 categorías), `libraries.yaml`, `repos.yaml`, `python_releases.yaml`, `top100.yaml`
  (generado).
- `data/runs/*.json` — registro por corrida; `revised_rows` mide correcciones de ClickPy.
- `src/ecopy/` — `sources/clickpy.py`, `sources/github.py`, `store.py`, `catalog.py`, `quality.py`, `validate.py`,
  `pipeline.py`, `metrics.py`, `site/`, `cli.py`, `models.py`.
- `tests/snapshots/` — HTML esperado; regenerar con `UPDATE_SNAPSHOTS=1 uv run pytest tests/test_site.py`.
- `docs/spikes/` — informe (`sN-*.md`) + script reproducible (`sN_*.py`) por spike: S1 cobertura,
  S2 versiones de Python, S3 estrellas, S4 ECharts vs Plotly, S5 Parquet + backfill, S7 correcciones
  y umbrales.
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
- Producto: `uv sync` · `uv run pytest` · `uv run ruff check . && uv run ruff format --check src tests`
  · `uv run ecopy ingest|validate|freeze|build|serve|stars|catalog --help`. Paquete en `src/ecopy/` (build backend `uv_build`), tests en `tests/`.
- Checks del toolkit: `scripts/bash/check_skill_symlinks.sh`, `check_hook_parity.sh`,
  `check_agent_parity.sh`; tests: `python3 scripts/hooks/test_<nombre>.py` (sin pytest).
- Spikes: scripts con dependencias inline (PEP 723), `uv run docs/spikes/<script>.py`. ClickPy:
  `https://sql-clickhouse.clickhouse.com/?user=play` (ver límites en Failed Approaches). S4 usa
  Google Chrome headless (`/usr/bin/google-chrome`).
- Git: el agente NUNCA hace add/commit/push/PR; entrega comandos, mensaje (`git commit -F`) y texto de PR.
  Commits agrupados: no uno por slice; seguir de corrido y entregar un commit al terminar lo pedido.
- Suggested skills: para la Etapa 1+ `tdd`, `codebase-design`;
  para diseño `impeccable` + `dataviz`; `handoff-doc` al cerrar.

---

## Session Log
> Sesiones anteriores al 2026-11-09: `docs/HANDOFF-ARCHIVE.md`.

### 2026-11-09 — Diseño de la Etapa 1 aprobado
Con `codebase-design`: interfaces de `sources.ClickPy`, `store.Store`, `metrics.library_view`,
`site.render_site` y `cli` (`ingest`/`build`/`serve`), seams y tests por módulo, 6 slices TDD.
Usuario aprobó las tres decisiones (normalized como vista, procedencia sellada por `store`,
`data/` versionado) → PRD (Módulos, Datos) actualizado.

### 2026-11-09 — Slice 1 (esqueleto) en verde
TDD: test de humo `ecopy --version` (RED: falta `ecopy.cli`) → `src/ecopy/cli.py` con argparse
(GREEN). `pyproject.toml` con `uv_build`, script `ecopy`, grupo dev (pytest 9.2, hypothesis,
ruff 0.17), config de ruff (excluye spikes y tooling). Sin dependencias de runtime todavía: cada
slice agrega las suyas. `pre-commit` del producto queda pendiente de decisión.

### 2026-11-09 — pre-commit del producto
Usuario aceptó versionar pre-commit: `.pre-commit-config.yaml` con hooks locales vía `uv run`
(ruff check --fix, ruff format, pytest), `pre-commit` en el grupo dev, fuera de `.gitignore`.
Primera corrida reformateó los spikes (pre-commit saltea `extend-exclude`): restaurados, y se
agregó `force-exclude` + `files: ^(src|tests)/`. `pre-commit run --all-files` en verde.

### 2026-11-09 — Slice 2 (`sources.clickpy`) en verde
TDD en 8 ciclos: `ClickPy(client, sleep=...).daily_downloads(projects, start, end)`. Consultas con
etiqueta (`/* ecopy:daily */`, `/* ecopy:checksums */`) para que el replay no dependa del SQL.
Mutaciones: quitar el control de lectura parcial o el cuadre rompe tests; `sum`→`max` no (replay),
pero contra ClickPy real da `ChecksumMismatch`. Fixture real: `fastapi` enero 2024 (31 días,
35.561.750 descargas, confirmado con consulta independiente). Agregado `httpx` como dependencia.

### 2026-11-09 — Slice 3 (`store`) en verde
TDD: `Store(root).append(batch, run)` y `.daily_downloads(projects)`. Se revisan todos los destinos
antes de escribir (sin archivos sueltos) y `os.link` impide pisar aun en carrera. El test "una
captura posterior corrige" pasó antes de implementar (el orden de archivos lo favorecía); lo
protege "el orden de escritura no decide", confirmado por mutación. `Run` valida id seguro como
nombre de archivo y `captured_at` con zona. Agregados `pyarrow` y `duckdb`.

### 2026-11-09 — Slice 4 (`metrics.library_view`) en verde
TDD en 7 ciclos + 5 propiedades con Hypothesis: serie mensual contigua hasta `as_of`, totales por
año (2016 parcial, año en curso YTD), último mes cerrado con datos. Decisión: un mes sin datos es
`None`, no 0 (el PRD no interpola huecos; en el gráfico es un corte). Agregado `pydantic`.

### 2026-11-09 — Slices 5–6: Etapa 1 completa en local
`site.render_site` (Jinja2, EN/ES, ECharts vendorizado con hash, `_headers`, snapshots) y `cli`
(`ingest`, `build`, `serve`). Corrida real de `fastapi` (2.891 días). Chrome headless: SVG dibujado,
sin violaciones de CSP (control positivo inyectando un script inline), tooltip con mes en curso,
sin desborde a 390 px, modo oscuro. Mutaciones: 2 sobrevivieron (proyecto `..`, salida con paquete
desconocido) → tests agregados. Paleta validada con el script de `dataviz`. Agregado `jinja2`.

### 2026-11-09 — Etapa 1 mergeada
Usuario mergeó el PR #3 (`909a376`, merge sin squash: `0c00df2` queda con su asunto incorrecto).
ROADMAP: Etapa 1 en *Shipped*, Etapa 2 como próxima. Sin código en curso.

### 2026-11-09 — Etapa 2 implementada en local
Diseño con `codebase-design`; usuario aprobó las 10 recomendaciones (PRD actualizado). Medido S7: 0
de 1,66 M de filas corregidas en ~40 h, umbrales de `validate`, lectura sin compactar. TDD de corrido:
`quality`, estados de período, store multi-dataset con escritura de cambios, fuentes nuevas, `catalog`,
`validate`, `pipeline`, aviso "Actualización fallida". Agregado `pyyaml`. Catálogo de 500 con borrador
del agente. Corrida real, Chrome headless sin violaciones de CSP y 24 mutaciones detectadas. Caída de
PyPI desde 2026-08-25 detectada al ampliar la medición: abierta. Sin commit: lo hace el usuario.

### 2026-11-09 — Etapa 2 mergeada; diseño de la Etapa 3 propuesto
Usuario mergeó el PR #4 (`5d184fc`). `docs/design/etapa-3-vista-anual.md` con evidencia medida sobre
`data/` y 6 decisiones, a la espera de aprobación. ROADMAP: Etapa 2 en *Shipped*; sus dos pendientes
pasan a la Etapa 3. Hallazgo: "Infraestructura base" domina los movers y el trío de Cloudflare sube
y baja lo mismo en 2025 y 2026.

### 2026-11-09 — Etapa 3 implementada en local
Usuario aprobó las 6 decisiones (PRD actualizado). `python_releases.yaml` verificado contra
endoflife.date y python.org; `year_view`, `ecopy freeze`, páginas por año EN/ES con 3 gráficos. Corrida
real sobre una copia para no congelar antes de revisar el catálogo. Corrección: las 24 mutaciones de
la Etapa 2 no eran válidas (arnés roto); con el arnés corregido, 5 de 54 sobrevivían y ahora tienen test.

### 2026-11-09 — Etapa 3 mergeada y años congelados
PR #5 mergeado. `ecopy freeze` corrido a pedido del usuario: 9 años en `data/frozen/`, sin commit y
con el catálogo sin cambios. Build completo en verde. Ingest del mismo día: 0 filas nuevas, esperado.
Próximo: diseño de la Etapa 4. El usuario aprobó traer la base visual a esa etapa y creó la rama.
Ramas locales de las Etapas 0–3 borradas tras confirmar que estaban mergeadas; las remotas quedan
para el usuario, porque borrarlas es un push. README y ROADMAP actualizados.

### 2026-11-09 — Etapa 4 implementada en local
Usuario aprobó las 9 decisiones y pidió una categoría "Otros". Vista previa de tres direcciones con
datos reales; ganó Estratos. TDD de corrido: `render.py` separado en `i18n`, `charts` y `svg`; base
visual; `repos.yaml` (486 con repo, 459 únicos); 176 librerías con tags; 7 pasan a `other` y
`data/frozen/` se regeneró; catálogo, dominios, categorías, comparador, releases, adaptador de GitHub y
`ecopy stars`. Mutaciones: 4 de 41 sobrevivían y ahora tienen test. Prueba real sin token sobre
`astral-sh/uv`: 163 semanas, suma = conteo. Sin commit: lo hace el usuario.
