# HANDOFF — ecopy (métricas históricas del ecosistema Python)
> Leer esto primero antes de tocar nada.
> Last updated: 2026-11-11 · branch: `etapa-6-logo-y-rankings` (desde `main` = `fbcb3b6`), **sin commit ni PR todavía**: los hace el
> usuario con `build/etapa-6-commit.txt` y `build/etapa-6-pr.md` (PR #9, #10 y #11 mergeados; el bot suma commits
> `data:` a diario, hacer `git pull` antes de trabajar) · sitio: https://ecopy.pages.dev · remoto `origin` =
> https://github.com/AndresPampa/ecopy.git

## Current State
- **Etapa 6 lista en la rama `etapa-6-logo-y-rankings`, sin commit (2026-11-11):** marca **eco-py** con la
  serpiente como guion (inline en `_base.html`, favicon nuevo) y nombre visible cambiado en todo el sitio;
  repo, comando, paquete y dominio siguen siendo `ecopy`. Dominios, categorías dentro de cada dominio e
  índice del comparador van de mayor a menor; movers no cambia. Las fichas, el comparador y los listados
  empiezan en la primera versión vigente en PyPI para 35 librerías (`catalog/series_start.yaml`).
  Porcentajes, crecimiento y puntos de cuota con 3 decimales. 434 tests, ruff limpio, 25 mutaciones
  detectadas (2 sobrevivían y ahora tienen test), Chrome sin violaciones de CSP en 56 combinaciones
  (14 páginas × claro/oscuro × 1280/390 px, con control positivo). `data/frozen/` sin cambios.
- **MVP publicado (Etapa 5 cerrada, 2026-11-10):** https://ecopy.pages.dev, desplegado por `update.yml`
  (PR #9). Verificado contra producción: `/` → `/en/` (302), CSP y cabeceras de `_headers`, 404 reales y
  Chrome sin violaciones de CSP (12 páginas × claro/oscuro × 1280/390 px, con control positivo). 405
  tests. Auditoría: `~/security-audit-skill/ecopy/run-1/REPORT.md`. Todavía no corrió ningún cron
  programado ni el paso `stars` en Actions: la primera ejecución fue manual y sin estrellas.
- **Ajustes visuales de la Etapa 4 mergeados** (PR #8): selector de tema (Pythonista =
  oscuro, Pythoneer = claro), créditos en el pie, cabecera alineada con el contenido y comparador
  vacío sin eje suelto. 345 tests, 5 mutaciones detectadas, Chrome sin violaciones de CSP (con control
  positivo) en los dos temas, a 1280 y 390 px.
- **Etapa 0 (spikes) mergeada** (PR #2): S1–S5 confirmados, informes en `docs/spikes/`.
- **Etapa 1 (tracer bullet, LOCAL) mergeada** (PR #3): los 6 slices están hechos, 73 tests en verde.
  `ecopy ingest → build → serve` funciona de punta a punta con datos reales de `fastapi` (2.891
  días, `data/` = 120 KB): página EN/ES con tabla anual, tabla mensual y gráfico ECharts,
  servida con la CSP real. Sin violaciones en Chrome headless (con control positivo), tooltip y
  móvil verificados. Diseño: `docs/design/etapa-1-tracer-bullet.md`.
- **Etapa 3 (vista anual, LOCAL) mergeada** (PR #5): 252 tests y 54 mutaciones con arnés
  corregido, sin violaciones de CSP en Chrome. `ecopy freeze` ya corrió en `data/` (2017–2025,
  metodología 1, sin commit) y `ecopy build` completo funciona: 500 fichas y 10 años en 9 s.
- **Etapa 4 mergeada** (PR #6 y #7): base visual (dirección Estratos), fichas ampliadas,
  catálogo con sparklines y filtro por tags, dominios y categorías, comparador, releases y `ecopy
  stars`. 340 tests, 41 mutaciones detectadas, Chrome sin violaciones de CSP (con control positivo).
  Build real: 500 fichas y 10 años, con estrellas. **Corrida real de estrellas completa** (2026-11-10):
  458 de 458 repos, 0 fallidos, 264.876 semanas; suma semanal contra total de GitHub con diferencia
  máxima de 3 estrellas. Las filas repetidas por clave son revisiones: gana la última. Los 9 nombres
  movidos ya están corregidos en `repos.yaml`; sus filas viejas quedan en `data/raw/github` sin usarse.
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
**Lo siguiente es el cierre anual (antes del 2027-01-01); logo, rankings y datos de fichas ya están en la rama.**
- [ ] **Usuario: commit, push y PR de la Etapa 6** con `build/etapa-6-commit.txt` y `build/etapa-6-pr.md`. Después del
      deploy, mirar en producción `/en/library/openai/` (debe empezar el 2020-02-18) y la marca en los dos temas.
- [ ] **Revisar las 15 librerías con descargas previas que NO se recortan** (promedio ≥ 100 por día antes de la primera
      versión vigente): `atomicwrites` (285 M: mismo proyecto, versiones borradas y vueltas a subir), `opencv-python`,
      `ortools`, `torch`, `lightning`, `tensorflow`, `flet`, `arcade`, `dvc`, `snowflake-connector-python`, `locust`,
      `darts`, `openai-whisper`, `backtrader`, `pymupdf`. Si alguna es un nombre reusado, hace falta una lista manual
      aparte: el umbral no distingue. `locust` y `backtrader` son los dudosos.
- [ ] **Al agregar librerías al catálogo, correr `uv run ecopy catalog starts`** (unas 500 consultas a la API JSON de
      PyPI, 1 a 2 minutos) y revisar el diff de `catalog/series_start.yaml`. `update.yml` no lo corre.
- [ ] **Decidir si las vistas anuales también descuentan lo anterior al inicio de serie.** Hoy `YearView` y
      `data/frozen/` siguen contando esas descargas (son ínfimas: openai sumó 2.173 en 2018). Cambiarlo obliga a
      regenerar `data/frozen/`.
- [ ] El usuario dijo "en todas lo vi mal" sobre los rankings, pero los listados de librerías ya salían de mayor a
      menor; se ordenaron las tres listas que no lo estaban. Si se refería a otra, falta saber cuál.
- [ ] **4. Antes del 2027-01-01: resolver el cierre anual, o el deploy diario se corta.** `update.yml` no corre
      `ecopy freeze`, y `ecopy build` falla con `FrozenYearMissing` en cuanto 2026 queda cerrado (`as_of` =
      2026-12-31, corrida del 1 de enero, `cli.py:_year_views`). Como `build` va antes del commit y del
      artefacto, no se publica ni se guardan datos hasta congelar. `freeze` además exige el top 100 del año
      (`ecopy catalog refresh`), que cambia `catalog/top100.yaml` y conviene revisar. Decidir: paso manual
      a principios de enero (y qué hace `build` mientras tanto) o automatizarlo.
- [ ] **Confirmar la primera corrida programada** (05:23 UTC) y la primera de estrellas
      (lunes 06:53 UTC) en Actions: revisar duración del paso `stars` contra `--max-minutes 25`.
- [ ] Opcional (endurecimiento del informe, sección 6): `wrangler` sin lockfile en el job con secretos;
      verificar que el artefacto no tenga `_worker.js`/`_routes.json`/`functions/`; `ValueError` y JSON
      inválido como `SourceError` en `github.py`; `validate._volume` con mediana 0; `.gitignore` para
      `*.pem`/`*.key`; `?tag=` sin `urlencode`.
- [ ] Más adelante: `python_minor` codificado (hex) solo si ClickPy empieza a traer 0x1e/0x1f. Al hacerlo,
      reproducir el escape TSV de ClickHouse (`'` → `\'`, `\\`) o migrar claves: hoy hay 2 valores
      guardados con `\'` que cambiarían de clave y duplicarían la fracción "otros" en `metrics`.
- [ ] **Usuario:** borrar la rama ya mergeada: `git branch -d docs-readme-arquitectura` y
      `git push origin --delete docs-readme-arquitectura`. No agregar `.wrangler/` (caché local) a ningún commit.
- [ ] Si cambia una categoría de `catalog/libraries.yaml`: borrar `data/frozen/` y volver a correr
      `uv run ecopy freeze`. `repo` y tags no lo invalidan.
- [ ] **Investigar la caída desde 2026-08-25** (−36 % de un día para el otro, recuperación lenta,
      algunos paquetes ×0,12). Ya está marcada como discontinuidad: si se explica, revisar esa marca.
- [ ] Opcional: activar hooks de Claude Code copiando `.claude/settings.template.json` →
      `.claude/settings.json` (hoy los guards solo corren en Codex).

### Ideas a futuro (pedidas por el usuario, sin fecha ni diseño)
- [ ] **Más fuentes de datos, incluso con scraping.** A definir cuáles; revisar términos de uso y licencia de cada
      sitio y sostener lo actual: procedencia por fila, atribución y nunca identidades de usuarios.
- [ ] **Detalle de las mejoras de cada release de Python:** qué agrega cada versión (novedades y mejoras), junto a la
      línea de tiempo actual (`catalog/python_releases.yaml` y `/python/`). El texto externo se sigue
      tratando como no confiable: autoescape, sin `|safe`, sin Markdown externo.

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

- **Etapa 5 (aprobado 2026-11-10):** `/` → `/en/` con `_redirects`; estrellas semanales (serie semanal,
  ~916 consultas contra 1.000/h del `GITHUB_TOKEN`); el bot commitea datos directo a `main`; sin el
  launcher de `impeccable`; auditoría de seguridad después de los workflows (perfil `standard`).
- **Skill `security-audit` instalado a mano** (no `npx skills add`) en `skills/security-audit`, commit
  `c1c8a8c`, MIT; notice en `skills/THIRD-PARTY-NOTICES.md`. Local e ignorado por git como el resto del tooling.
- **Marca eco-py (decisión del usuario, 2026-11-11):** las tres variantes de ChatGPT se descartaron (dos eran el logo
  de Python recoloreado, y la PSF exige permiso incluso para cambios de color; el PNG se borró). Eligió la opción
  "Guion" y pidió el nombre eco-py en todo el sitio. El favicon lleva colores fijos y nada de `<style>`.
- **Series desde la primera versión vigente (decisión del usuario, 2026-11-11):** "no mostremos cosas que no son".
  Se corta la serie y una nota dice cuántas descargas quedan fuera; los datos crudos no se tocan.
- **Movers queda por cambio de cuota** (aceptado por el usuario): por descargas, la mayor suba de 2025 quedaba cuarta.
- **3 decimales en porcentajes** (pedido del usuario): con 1 decimal las cuotas chicas salían 0,0 %.
- **Selector de tema (decisión del usuario, 2026-11-10):** el botón nombra el tema al que cambia. Sin
  elección guardada manda el sistema. `theme.js` va sin `defer` para no parpadear y la CSP no cambia.
  La paleta oscura está duplicada porque `getComputedStyle` devolvería `light-dark(...)` crudo a los
  gráficos; un test exige que los dos bloques coincidan.

## Failed Approaches
- **"Primera subida que figura en PyPI" no es "primera versión de la librería":** PyPI no lista versiones borradas.
  De 500 paquetes, 50 tienen descargas anteriores; en unos es un nombre reusado (`uv`, `mcp`, `openai` con una `0.1`
  de 2018) y en otros el mismo proyecto con versiones viejas borradas (`atomicwrites`, 285 M de descargas previas).
  Recortar las 50 borraría historia real: por eso el umbral de 100 descargas por día (`catalog.TRACE_DAILY`).
- **Las capturas por CDP a menos de ~1 s salen a mitad de la animación de ECharts:** la línea de `openai` parecía
  cortarse en 2024 y las barras no coincidían con la tabla. Esperar o usar `--virtual-time-budget`.
- **El entorno de GitHub se tiene que llamar exactamente como en el workflow:** con los secretos en `prd`
  y `environment: production`, GitHub creó `production` vacío al correr y wrangler falló con "necessary
  to set a CLOUDFLARE_API_TOKEN". Los secretos no se copian entre entornos: hay que volver a cargarlos.
- **Un fixture de git que reusa el bare como `origin` no prueba el push con token:** `git push origin`
  pasaba igual que `git push "$REMOTE"`. En `tests/test_workflows.py` el `origin` del clon apunta a una
  ruta inexistente, como queda en Actions con `persist-credentials: false`. Lo reveló una mutación.
- **Sandbox de la auditoría:** un `--tmpfs /tmp` de `bwrap` sin `--size` deja escritura sin tope (no
  cuenta para `RLIMIT_AS`); lo detectó el reconocimiento y se corrigió antes de cazar. Las herramientas
  quedaron en `~/security-audit-skill/ecopy/run-1/tools/` (`sandbox.sh`, `promote.py`, generadores).
- **Medir desborde con `scrollWidth > innerWidth` no sirve con barra de desplazamiento clásica:**
  `innerWidth` la incluye y tapa desbordes de hasta 15 px. Usar `clientWidth` y
  `Emulation.setScrollbarsHidden`; sin eso, las capturas por CDP a 390 px salen recortadas a 375.
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
- `README.md` — propósito, tecnologías y 4 diagramas Mermaid (datos, actualización diaria, módulos, del
  cambio a producción). Si cambia el flujo o una dependencia entre módulos, actualizarlos.
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
- `catalog/series_start.yaml` — inicio de serie de 35 librerías (generado por `ecopy catalog starts`).
- `src/ecopy/sources/pypi.py` — primera subida vigente de un paquete (API JSON de PyPI).
- `build/preview-logo/` (ignorado) — las dos rondas de opciones de logo.
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
- Auditoría de seguridad: salida y herramientas en `~/security-audit-skill/ecopy/run-1/` (fuera del repo).
  Una segunda corrida del skill usaría `run-2` y leería el ledger y `findings.json` de `run-1`.
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

### 2026-11-10 — Corrida real de estrellas completa
Tres corridas con token: 4.000, 4.000 y 2.342 consultas, 1 h 30 cada una de las dos primeras (unos
1,35 s por consulta, no 1 s). Otra corrida previa sin token se cortó en 50 consultas y se solapó 14 s
con la primera, sin daño: el store no reescribe lo que ya tiene. 459 repos completos y 0 fallidos.
`--budget` cuenta también los `observed` de los repos ya completos (unas 2 consultas por repo). 9 repos
movidos: corregidos en `repos.yaml` y 8 bajados de nuevo con `--repo` (165 consultas); `pypdf2` pasa a
compartir repo con `pypdf`. Quedan 458 repos únicos. Build con estrellas: 486 fichas con repo, 14 sin él.
Los tests se corren con `uv run pytest`: con `.venv/bin/python -m pytest` falla el del comando `ecopy`
porque el ejecutable no está en el PATH.

### 2026-11-10 — Etapa 4 mergeada; próximos ajustes visuales
PR #6 (código y años congelados) y #7 (estrellas y nombres de repos corregidos) mergeados; `main` =
`bd4affe`. El usuario hizo el chequeo visual y encontró cosas para arreglar: las detalla en la próxima
sesión, en la rama `etapa-4-ajustes-visuales`. README y ROADMAP actualizados.

### 2026-11-10 — Ajustes visuales de la Etapa 4
A pedido del usuario: selector de tema Pythonista/Pythoneer con elección persistente, créditos en el pie
(GitHub, Instagram y código fuente), marca de la cabecera alineada con el contenido y comparador vacío
sin eje suelto. TDD para lo que sale en el HTML y Chrome por CDP para el comportamiento del JavaScript,
porque el proyecto no tiene runner de JS. El launcher de `impeccable` no se ejecutó. Sin commit.

### 2026-11-10 — Ajustes mergeados; ingest real y propuesta de la Etapa 5
PR #8 mergeado (`b4bc017`). `ecopy ingest` real en 7,5 s: 500 + 1 filas nuevas, 0 corregidas, datos hasta
2026-11-09; cierra el pendiente de la Etapa 2, aunque una sola corrida no mide correcciones a lo largo
del tiempo. Relevado lo que falta para publicar; la propuesta espera aprobación. Sin código nuevo.

### 2026-11-10 — Etapa 5: slices 1-4 y auditoría de seguridad
TDD de corrido: `_redirects`, 404 EN/ES (y `ecopy serve` las sirve), favicon, descripción, canonical,
hreflang, sitemap y robots; metodología EN/ES con fechas tomadas de `quality.py`; accesibilidad medida
en Chrome (contraste sin fallas; desbordes a 320 px, objetivos táctiles y salto al contenido
corregidos); workflows con tests de garantías y 8 mutaciones detectadas. Auditoría con el skill de
Cloudflare: sandbox `bwrap` propio y promotor de artefactos; 2 olas de cazadores, 3 críticos, fases 3 y 5
independientes. El hallazgo más relevante es de diseño de `update.yml` (dispatch en otra rama llega a
`main` y a producción), que depende de la configuración de GitHub. Sin commit.

### 2026-11-10 — Arreglos de la auditoría de seguridad
TDD de corrido sobre los 4 puntos. (1) `ClickPy`: `MalformedResponse` (`SourceError`) para resumen
inválido en `_query` y cuerpos con otra forma vía `_parsing`; `ingest` registra `internal_error` y relanza.
(2) `update.yml`: `if` de `main` en update y deploy, checkout `ref: main` con `persist-credentials: false`,
push por `$REMOTE` (URL con `github.token`, solo en ese paso) y guarda de un solo commit; el script se
prueba ejecutándolo contra un bare local. (3) `github.py`: `retry-after` > 120 s, negativo, no finito o
ilegible → `RateLimited` (la doc de GitHub advierte bloqueo si se reintenta estando limitado); `deadline`
+ `clock`, `ecopy stars --max-minutes 25`, `timeout-minutes: 30` del paso. (4) Consulta de solo lectura a
ClickPy: 0 filas con 0x1e/0x1f (ni tab/salto) en `python_minor`; la validación de 3 campos ya la da el
punto 1 y la codificación queda para después (ver Next Steps). 20 mutaciones, todas detectadas tras sumar
2 casos (resumen en `known_projects`, token a nivel job). Chrome: 48 combinaciones sin fallas.

### 2026-11-10 — Etapa 5 mergeada (PR #9)
El usuario hizo el commit único (`1622537`) y mergeó el PR #9; `main` = `b48ceb3`. Queda S6 y el primer
deploy. Este handoff y el ROADMAP se actualizaron sobre `main` sin commit.

### 2026-11-10 — MVP publicado
S6 hecho por el usuario. El primer deploy falló por el entorno `prd` (ver Failed Approaches); con
`production` configurado y "Re-run failed jobs" salió bien. Chequeos contra `ecopy.pages.dev` sin fallas.
Etapa 5 pasa a Shipped en el ROADMAP.

### 2026-11-10 — README con propósito, tecnologías y arquitectura
PR #10 mergeado; ramas viejas ya borradas. README reescrito: propósito (mirada global y holística del
ecosistema), estado publicado, 4 diagramas Mermaid y tabla de tecnologías; BigQuery aclarado como respaldo
no implementado. Diagramas renderizados con Mermaid 11.4.1 en Chrome, claro y oscuro, a 830 px. Al relevar
el flujo apareció que `update.yml` no congela años: ver Next Steps. Sin código nuevo.

### 2026-11-10 — Cierre de sesión: pedidos para la próxima
PR #11 mergeado (`fbcb3b6`). El usuario fijó el orden: logo con `impeccable`, rankings de mayor a menor y, como
slice aparte, los errores de gráficos; después el plan. Anotadas dos ideas a futuro: más fuentes con scraping
y las mejoras de cada release de Python. Relevado sin cambiar código: catálogo y categorías ya están
ordenados por descargas, así que falta saber dónde lo vio mal el usuario. Sin código nuevo.

### 2026-11-11 — Etapa 6: logo eco-py, rankings, inicio de series y decimales
Rama `etapa-6-logo-y-rankings`. Logo en dos rondas con `impeccable` (sin launcher); el usuario eligió el guion-serpiente
y el nombre eco-py. Rankings: se ordenaron dominios, categorías por dominio e índice del comparador. El "error" de
`openai` desde 2018 eran descargas reales de una versión `0.1` borrada: adaptador de PyPI, `ecopy catalog starts` y
corte de la serie con nota. Porcentajes con 3 decimales. TDD de corrido, mutaciones y Chrome por CDP. Sin commit.
