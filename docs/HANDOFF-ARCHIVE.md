# HANDOFF — entradas anteriores del Session Log

> Sesiones del 2026-11-05 al 2026-11-07. Lo vigente está en `docs/HANDOFF.md`.

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

### 2026-11-07 — S5 confirmado; Etapa 0 mergeada; arranca la Etapa 1
Usuario commiteó y mergeó la Etapa 0 (PR #2, `a54967c`) y creó `etapa-1-tracer-bullet`. Confirmó
S5 → PRD (Datos: tamaño, serie diaria, disposición, versión de Python global; Fuentes: reglas del
adaptador de ClickPy; Further Notes), informe y ROADMAP actualizados. Etapa 0 colapsada en
*Shipped*. Usuario decidió probar todo en local hasta un primer MVP: Etapa 1 sin Actions ni
Cloudflare; GitHub Actions + Cloudflare Pages (S6) movidos a la Etapa 5 (ROADMAP, README).
