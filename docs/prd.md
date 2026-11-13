# PRD — ecopy: el ecosistema Python, año por año

> Estado: **CERRADO** (revisado por el usuario) · 2026-11-06
> Fuente: sección "Key Decisions & Why" de `docs/HANDOFF.md` (no `brainstorming.md`, desactualizado).
> Etiqueta de triage prevista: `ready-for-agent` (cuando exista un tracker).

## Problem Statement

Quien quiere entender cómo evoluciona el ecosistema Python —qué librerías crecen, cuáles pierden
terreno, qué versiones del lenguaje se adoptan, qué categorías ganan peso— no tiene un lugar único,
gratuito y con histórico largo donde verlo. Los datos existen (descargas de PyPI vía linehaul,
releases, GitHub), pero están dispersos, en crudo, y las vistas disponibles muestran sobre todo el
presente o ventanas cortas. Las cifras brutas además engañan: el volumen de descargas está inflado
por CI y crece año a año por razones ajenas a la popularidad real, y los rankings simples sufren
sesgo de supervivencia (solo muestran a quien sigue arriba hoy).

El desarrollador, por su parte, quiere construir y mantener esto solo, con presupuesto cero y sin
servidores que operar.

## Solution

**ecopy** ("the Python ecosystem, year by year") es un sitio estático, bilingüe (EN/ES), regenerado
una vez al día, publicado en `ecopy.pages.dev`. Ofrece:

- Una **vista anual** desde 2017: cuota de descargas por categoría (neutraliza la inflación por CI),
  movers, recién llegados, adopción de versiones de Python, línea de tiempo del lenguaje y volumen
  total con advertencia explícita.
- **Fichas de librerías** de un catálogo de ~500 paquetes con su historia de descargas.
- **Releases de Python** en una línea de tiempo.
- Un **comparador simple** entre librerías.
- Una página de **metodología** que explica fuentes, cálculos, sesgos y versiones metodológicas.
- **Estrellas de GitHub** por librería, con su historia semanal.
- **Categorías en dos niveles** (dominios → subcategorías) con página propia, y **tags** para descubrir
  librerías por característica.

Todo se genera en un pipeline diario sin servidor: GitHub Actions → ingesta Python → almacenamiento
append-only en Parquet → cálculo de métricas → render HTML → Cloudflare Pages.

## User Stories

### Lector: vista anual
1. Como lector, quiero elegir un año desde 2017, para ver cómo estaba el ecosistema ese año.
2. Como lector, quiero ver la cuota de descargas por categoría en un año, para comparar el peso relativo de áreas (web, datos, ML, testing…) sin que la inflación por CI distorsione.
3. Como lector, quiero ver los "movers" del año (mayores subidas y bajadas de posición/cuota), para detectar tendencias.
4. Como lector, quiero ver los recién llegados al top del año, para descubrir librerías emergentes.
5. Como lector, quiero ver la adopción de versiones de Python por año, para saber cuándo una versión se volvió mayoritaria.
6. Como lector, quiero ver una línea de tiempo del lenguaje (releases, fin de soporte), para contextualizar los cambios de adopción.
7. Como lector, quiero ver el volumen total de descargas con una advertencia visible y la discontinuidad de 2018-07-27 marcada, para no interpretarlo como crecimiento de usuarios reales ni comparar a través de un cambio de recolección.
8. Como lector, quiero que el año en curso se muestre como YTD comparado con el mismo período del año anterior, para no comparar un año parcial contra uno completo.
9. Como lector, quiero que los rankings de años cerrados no cambien entre visitas, para poder citarlos con confianza.
10. Como lector, quiero ver qué versión metodológica produjo cada ranking anual, para entender por qué dos años podrían no ser comparables.
11. Como lector, quiero que no haya un "puntaje combinado" opaco, para interpretar cada métrica por separado.

### Lector: librerías
12. Como lector, quiero navegar el catálogo por dominio y categoría, para encontrar las librerías de mi área.
13. Como lector, quiero una ficha por librería con su serie histórica de descargas, para ver su trayectoria desde 2016 (2016 marcado como parcial).
14. Como lector, quiero ver sparklines en listados, para comparar trayectorias de un vistazo.
15. Como lector, quiero ver que una librería renombrada enlaza con su nombre anterior, para seguir su historia completa.
16. Como lector, quiero que los renombres no se sumen automáticamente, para no ver cifras infladas o mezcladas.
17. Como lector, quiero ver las estrellas de GitHub de una librería y su evolución semanal, para tener una señal complementaria a las descargas.
18. Como lector, quiero que las librerías que fueron top en años pasados sigan apareciendo aunque hayan caído, para evitar sesgo de supervivencia.

### Lector: comparador y releases
19. Como lector, quiero comparar dos o más librerías en un mismo gráfico, para decidir entre alternativas.
20. Como lector, quiero que el comparador funcione sin servidor (datos ya generados), para que cargue rápido y sea enlazable.
21. Como lector, quiero ver los releases de Python en orden cronológico con sus fechas clave, para ubicar eventos del lenguaje.

### Lector: confianza, idioma, acceso
22. Como lector, quiero una página de metodología con fuentes, fórmulas, sesgos conocidos y versiones, para evaluar la calidad del dato.
23. Como lector, quiero ver la atribución a PyPI/linehaul y ClickPy, para saber de dónde vienen los datos.
24. Como lector, quiero ver la fecha de última actualización, para saber qué tan fresco es el dato.
25. Como lector, quiero ver un aviso "Actualización fallida" cuando la última ingesta no pasó validación, para no confundir datos viejos con actuales.
26. Como lector hispanohablante, quiero el sitio completo en español, para leerlo en mi idioma.
27. Como lector anglohablante, quiero el sitio completo en inglés, por la misma razón.
28. Como lector, quiero que las páginas carguen rápido y se indexen en buscadores, para encontrarlas y usarlas desde el móvil.
29. Como lector, quiero que los gráficos sean accesibles (contraste, modo claro/oscuro, texto alternativo), para leerlos en cualquier condición.

### Mantenedor (desarrollador solo)
30. Como mantenedor, quiero que todo el pipeline corra en un cron diario de GitHub Actions, para no operar servidores.
31. Como mantenedor, quiero costo cero de infraestructura, para sostener el proyecto sin presupuesto.
32. Como mantenedor, quiero un backfill único desde 2016-01-22 (todo lo disponible) vía ClickPy, para tener el histórico sin pagar BigQuery.
33. Como mantenedor, quiero poder reconstruir el histórico desde BigQuery como respaldo, para no depender de un único proveedor.
34. Como mantenedor, quiero que cada fila guardada tenga procedencia (`source`, `acquisition=backfill|observed`, `captured_at`, `ingestion_run_id`), para auditar cualquier cifra.
35. Como mantenedor, quiero que el almacenamiento sea append-only, para que una corrida mala nunca destruya datos previos.
36. Como mantenedor, quiero que las correcciones de la fuente se registren como archivos nuevos, para conservar lo observado originalmente.
37. Como mantenedor, quiero que las métricas se recalculen en cada build desde los datos normalizados, para que un cambio de fórmula se aplique sin migraciones.
38. Como mantenedor, quiero guardar en cada corrida la historia reciente de estrellas y el `stargazers_count` del día, para conservar también el valor bruto (la historia de GitHub es neta: descuenta estrellas retiradas).
39. Como mantenedor, quiero definir el catálogo curado en YAML (categoría principal y tags en `libraries.yaml`, repo de GitHub en `repos.yaml`), para editarlo sin tocar código.
40. Como mantenedor, quiero que el catálogo se complete automáticamente con la unión del top 100 de cada año, para no depender solo de mi criterio.
41. Como mantenedor, quiero declarar renombres en el catálogo, para enlazar historias sin sumarlas.
42. Como mantenedor, quiero que, si la validación falla, se publique el sitio del día anterior con el aviso de fallo, para nunca publicar datos rotos.
43. Como mantenedor, quiero un CLI con comandos separados (ingestar, construir, validar), para correr cada etapa localmente.
44. Como mantenedor, quiero consultar ClickPy con moderación (límite de ritmo), para ser un buen ciudadano de un servicio gratuito.
45. Como mantenedor, quiero que las opciones de gráficos se generen desde modelos tipados, para detectar errores al construir y no en el navegador.

### Categorías y tags
49. Como lector, quiero una página por categoría con su ranking interno, movers, recién llegados y la evolución de su cuota, para seguir mi área año a año.
50. Como lector, quiero ver la cuota por dominio (Data & AI, Development, …) y bajar a sus categorías, para entender el panorama sin perderme en decenas de categorías.
51. Como lector, quiero filtrar librerías por tags (p. ej. `async`, `dataframe`), para descubrir librerías por característica sin importar su categoría.
52. Como mantenedor, quiero que cada librería tenga exactamente una categoría principal, para que las cuotas por categoría y por dominio sumen 100 % sin contar dos veces una descarga.
53. Como mantenedor, quiero que los tags salgan de un vocabulario controlado, para que no deriven en sinónimos (`ml`/`machine-learning`).

### Seguridad y privacidad
46. Como usuario de GitHub, quiero que ecopy nunca persista identidades de usuarios (solo conteos), para que mi actividad no quede expuesta.
47. Como lector, quiero que el sitio no ejecute contenido externo inyectado, para estar a salvo de XSS (autoescape, sin `|safe` en campos externos, sin Markdown externo, solo URLs https, CSP estricta).
48. Como mantenedor, quiero Actions fijadas por SHA, permisos mínimos por job y sin `pull_request_target`, para reducir el riesgo de supply chain.

## Implementation Decisions

**Arquitectura**
- Sitio 100 % pre-generado; sin servidor en runtime. Evidencia: los datos cambian 1×/día y todo es de lectura → costo cero, CDN, SEO, menor superficie de ataque. FastAPI queda reservado para una futura API pública; Supabase para Fase 4 (auth/encuestas), porque su free tier de 500 MB no alcanza para el histórico diario.
- Pipeline: GitHub Actions (cron diario, repo público bajo la cuenta del usuario) → ingesta → normalización → métricas → render → deploy a Cloudflare Pages (`ecopy.pages.dev`, sin dominio pago).

**Módulos** (profundos, con interfaces pequeñas; `site` nunca toca `store`)
- `sources` — adaptadores por proveedor (ClickPy, BigQuery de respaldo, GitHub). Las fechas de releases de Python van en `catalog/python_releases.yaml`, curado: ~25 filas que cambian una vez por año. Entrada: rango de fechas/paquetes. Salida: registros tipados, completos y verificados, con la fuente (`source`) por lote; ante un resultado parcial o que no cuadra, una excepción, nunca datos incompletos. No conoce `acquisition` ni la política de ventanas (las decide `cli`). Toda la E/S HTTP pasa por un cliente `httpx` inyectable.
- `store` — escritura append-only de Parquet particionado y lectura vía DuckDB. Nunca sobrescribe; una corrección es un archivo nuevo. Sella la procedencia de cada archivo a partir de la corrida (`Run`: id, `captured_at`, `acquisition`) que le pasa `cli`. Expone una vista de solo lectura del dataset normalizado: **`normalized` es una vista** (deduplicación + la corrección más reciente gana por paquete y fecha), no una capa física; se materializa recién cuando haya una segunda fuente que mapear o la lectura sea lenta (diseño de la Etapa 1, `docs/design/etapa-1-tracer-bullet.md`).
- `catalog` — carga y valida el YAML curado, la taxonomía y el top 100 anual (archivo generado con `ecopy catalog refresh` y revisado por diff: los años cerrados quedan fijos), resuelve categorías y renombres (enlaces, no sumas).
- `metrics` — funciones puras sobre el dataset normalizado + catálogo: cuota por categoría, movers, recién llegados, adopción de versiones, YTD vs mismo período, rankings anuales congelados con versión metodológica. Sin puntaje combinado.
- `site` — recibe únicamente modelos de vista (Pydantic) producidos por `metrics`; renderiza Jinja2 (autoescape) + opciones de ECharts serializadas desde Pydantic + sparklines SVG generadas en Python; i18n EN/ES; emite `_headers` con CSP.
- `quality` — calendario de huecos y días degradados de la fuente (constante documentada, puro). Reemplaza al flag físico: un hueco no tiene filas donde marcarlo y los períodos son globales.
- `validate` — reglas puras sobre lo que se va a escribir y la historia: volumen del día (0,4–2,0 de los mismos días de semana previos), ≥ 98 % de los paquetes esperados, ningún paquete por encima del total del día, versiones contra total (≤ 0,5 %) y atraso ≤ 3 días.
- `pipeline` — orquesta la ingesta: ventana por paquete (sin datos → backfill; con datos → reobserva los últimos 7 días), validación **antes** de escribir y registro de la corrida en `data/runs/<id>.json`.
- `cli` — parser y raíz de composición: `ingest` (el backfill se decide por paquete, no es un comando), `validate`, `build`, `serve`, `catalog refresh|check`. Una corrida rechazada no entra al store: `build` reconstruye con las cifras anteriores y el aviso "Actualización fallida" (diseño de la Etapa 2).

**Datos**
- Esquema de procedencia por fila: `source`, `acquisition` (`backfill` | `observed`), `captured_at`, `ingestion_run_id`. Un archivo = una corrida → procedencia constante dentro del archivo (en S5 costó ~0 bytes).
- Particionado por fuente y fecha dentro del repo (`data/`, versionado desde la Etapa 1): `raw/<fuente>/<dataset>/year=YYYY/<run_id>.parquet`. Git LFS descartado. Tamaño medido (spike S5):
  ~500 paquetes desde 2016-01-22 ≈ 10 MB en Parquet (zstd) y ~3 MB/año de ingesta; ≤ 125 MB a
  10 años en el peor supuesto → **alcanza el repo, R2 no se activa**. Se reevalúa si `data/`
  supera 500 MB o algún archivo pasa 50 MB (GitHub bloquea a 100 MB), o si lo exigen los
  términos de ClickPy.
- Se guarda la **serie diaria** de descargas (la mensual se deriva en `metrics`): hace falta para
  YTD vs mismo período y para marcar huecos. Disposición: cada corrida escribe un archivo por año
  que toca (`year=YYYY/<run_id>.parquet`): el backfill deja ~11; la ingesta diaria, uno chico.
- Adopción de versiones de Python (historia 5): agregado global de todo PyPI, mensual y solo de
  meses cerrados; se trae cuando falta un mes (cada pasada lee 10.644 M de filas). El desglose
  por paquete no se guarda en el MVP (2,65 MB si se pide después).
- Año calendario en UTC. Rankings de años cerrados se congelan junto con su versión metodológica: `ecopy freeze` guarda la vista anual completa en `data/frozen/year=YYYY/methodology=N.json`. Hasta que se congela (paso manual de enero, después de `ecopy catalog refresh` y de revisar el top 100), un año recién cerrado se publica como "cierre provisional", recalculado en cada build. Las cuotas se calculan sobre el total del catálogo; movers y recién llegados excluyen "Infraestructura base".
- Cobertura (spike S1): datos diarios desde 2016-01-22. Vistas anuales desde **2017** (primer año
  completo); 2016 solo en fichas, marcado como parcial. Las métricas relativas (cuota, rankings,
  movers) son comparables a través del salto ×3 de volumen del 2018-07-27 (cuotas estables); los
  crecimientos de volumen absoluto que lo crucen no se calculan.
- Discontinuidades de volumen (2018-07-27 y 2026-08-25): se marcan y no se calcula crecimiento absoluto que las cruce.
- Calidad del dato: huecos (2016-03-06→05-21, 2019-04-26/27) y días degradados (2018-07-11→26, más 2016-12-08, 2017-05-11, 2018-04-17, 2019-04-13, 2019-04-25 y 2019-04-28) se marcan en el calendario de `quality`, no se borran ni se interpolan. Un día sin filas de un paquete son cero descargas, no un hueco de la fuente.
- La ingesta diaria toma hasta ayer (UTC) y reobserva los últimos 7 días guardados; el store solo
  escribe filas nuevas o que cambiaron (medido: 0 de 1,66 M de filas cambiaron en ~40 h).
- Estrellas de GitHub (spike S3): `GET /repos/{o}/{r}/stargazers/history` (semanas con días, 30 por
  página, neto; cuadra exacto con `stargazers_count`). Backfill una vez (~9.000 consultas para ~500
  repos, repartido en varias corridas) y en cada corrida la página 1 + `stargazers_count`, con el
  `GITHUB_TOKEN` de Actions (el backfill se corre en local con un token personal, 5.000/h: ver
  `docs/design/etapa-4-librerias-y-comparador.md`). Comando aparte de `ingest`. Solo conteos; nunca logins ni IDs de usuarios. El listado con
  `starred_at` quedó descartado (exige autenticación de admin/colaborador desde julio de 2026).

**Fuentes**
- Límites de la instancia pública de ClickPy (S2): resultados parciales **sin error** si se leen > 10.000 M de filas o se devuelven > 1.000 filas. El adaptador verifica el resumen de cada consulta, pagina y lee tablas grandes por rangos de `project`.
- Reglas del adaptador de ClickPy (spike S5, `docs/spikes/s5-parquet-backfill.md`):
  - Siempre `GROUP BY` + `sum(count)`: la tabla diaria es SummingMergeTree y tiene filas
    duplicadas por (paquete, día) hasta que el servidor fusiona partes.
  - Pedir `wait_end_of_query=1`: sin él, el resumen `X-ClickHouse-Summary` sale con el primer
    bloque y no informa filas ni bytes del resultado.
  - Una fila por paquete con la serie en un array, lotes de ≤ 50 paquetes (~5 MB; el límite de
    10 MB no corta de forma fiable), y cada lote se cuadra contra sumas de control calculadas en
    el servidor. Backfill de 500 paquetes: ~10 consultas para la serie diaria.
- ClickPy (usuario `play`, gratis) como fuente principal del backfill desde 2016-01-22 (inicio de los datos; ver `docs/spikes/s1-clickpy-cobertura.md`). Sin solicitar permiso: el dato es público (PyPI/linehaul); se atribuye y se limita el ritmo.
- BigQuery (`pypi` público) solo como respaldo reproducible, porque cobra por bytes escaneados.

**Taxonomía**
- Dos niveles: **dominio** → **categoría**. Cada librería tiene **exactamente una categoría
  principal** (las cuotas suman 100 %) y **tags** opcionales de vocabulario controlado, que sirven
  para navegar y filtrar pero **nunca entran en métricas**.
- Dominios y categorías (propuesta del usuario; lista fina pendiente de cerrar al armar el catálogo
  en la Etapa 2):
  - **Data & AI:** Machine learning e IA · LLMs e IA generativa · Ciencia de datos · Ingeniería de
    datos · Big Data · NLP · Estadística y econometría · Series temporales y forecasting ·
    Visualización · MLOps.
  - **Development:** Desarrollo web · Aplicaciones interactivas y dashboards · Clientes HTTP y APIs · Aplicaciones de escritorio · CLI y
    terminal · Herramientas de desarrollo · Testing · Documentación · Serialización y validación.
  - **Infrastructure & Operations:** Cloud y DevOps · Bases de datos y ORMs · Mensajería y streaming ·
    Sistemas distribuidos · Seguridad y criptografía · Monitoreo y observabilidad · Infraestructura
    base.
  - **Multimedia & Specialized:** Imagen y multimedia · Audio y video · Geoespacial y GIS ·
    Computación científica · Robótica e IoT · Juegos y simulación · Finanzas cuantitativas ·
    Optimización y matemática.
  - **Utilities:** Scraping y automatización · Gestión de archivos y documentos · Configuración ·
    Internacionalización · Generación de datos sintéticos.
- Identificadores estables (slug) por dominio, categoría y tag, con etiquetas EN/ES; renombrar una
  etiqueta no rompe URLs ni históricos.
- Cambiar la categoría de una librería es un cambio metodológico: no altera rankings anuales ya
  congelados.
- "Infraestructura base" agrupa dependencias que casi nadie instala a propósito (`urllib3`,
  `certifi`, `six`…), para que no inflen otras categorías.

**Frontend**
- Python-first: Jinja2 + ECharts + SVG. Descartados Dash/Streamlit/Reflex/NiceGUI (requieren servidor) y PyScript (peso).
- Gráficos (spike S4): **ECharts 6.x, build `common`** (195 KB brotli; Plotly basic 324 KB e
  inyecta `<style>` inline, incompatible con la CSP sin parche). Versión fija, **servida desde el
  propio sitio** y verificada con hash al construir (mantiene `script-src 'self'`, sin depender de
  un CDN). Renderer SVG. Si la vista anual pide un tipo que `common` no trae (treemap, heatmap),
  pasar a `full` (+97 KB) antes que un build a medida con Node.
- Diseño guiado por los skills `impeccable` y `dataviz`.

## Testing Decisions

**Qué es un buen test aquí:** verifica comportamiento observable en un seam público (registros devueltos, archivos escritos, HTML generado), nunca detalles internos (nombres de funciones privadas, consultas SQL exactas, estructura interna de DataFrames).

**Seams acordados (de más alto a más bajo):**
1. **CLI end-to-end (humo):** `ingest` + `build` sobre fixtures HTTP grabadas → directorio de sitio generado. Se afirma: páginas clave existen en EN/ES, contienen cifras esperadas, `_headers` trae la CSP, y con validación fallida se publica el build anterior con el aviso.
2. **`sources` (contrato):** cada adaptador contra respuestas fijas vía `httpx.MockTransport`; se afirma el mapeo a registros tipados con procedencia y el manejo de errores/rate limit. Sin red real en CI.
3. **`store` (inmutabilidad):** sobre un directorio temporal; escribir dos veces o escribir una corrección nunca modifica archivos existentes; la lectura refleja la última corrección.
4. **`metrics` (unitarios puros + propiedades con Hypothesis):** p. ej., las cuotas por categoría suman 1; los rankings congelados no cambian al agregar datos posteriores; los renombres nunca se suman; YTD compara ventanas de igual longitud.
5. **`site` (snapshots):** modelos de vista fijos → HTML/opciones ECharts comparados con snapshots; tests de que campos externos con `<script>` salen escapados.

`catalog` se cubre con unitarios puros (YAML de ejemplo → categorías, unión de top-100, renombres) y validaciones: toda librería tiene exactamente una categoría existente, todo tag pertenece al vocabulario, todo paquete existe en PyPI. En `metrics`, las cuotas por categoría y por dominio suman 1.

**Prior art:** no hay código del producto aún. El único antecedente en el repo son los tests de hooks del tooling (script Python plano, sin pytest), que no aplican como patrón; el proyecto adoptará `pytest` + `hypothesis`.

## Out of Scope

- Trending y Seguridad (Fase 3).
- Autenticación, cuentas, encuestas (Fase 4, Supabase).
- API pública (FastAPI, futura).
- Dominio propio pago.
- Publicar en PyPI.
- Puntajes combinados o "índices de popularidad" que mezclen métricas.
- Cualquier dato de identidad de usuarios de GitHub.
- Métricas calculadas sobre tags (solo navegación).

## Further Notes

**Fase 0 (spikes que condicionan este PRD):**
- ~~Cobertura de años y calidad del dato antiguo en ClickPy.~~ Resuelto en S1 (`docs/spikes/s1-clickpy-cobertura.md`): desde 2016-01-22; vistas anuales desde 2017.
- ~~Si ClickPy desglosa por versión de Python.~~ Resuelto en S2 (`docs/spikes/s2-clickpy-versiones-python.md`): sí, desde 2016; historia 5 confirmada, granularidad mensual.
- ~~Fuente de histórico de estrellas.~~ Resuelto en S3 (`docs/spikes/s3-github-estrellas.md`): existe `stargazers/history`; historia 17 confirmada.
- ~~Peso real de ECharts vs Plotly en un prototipo de ranking + ficha.~~ Resuelto en S4 (`docs/spikes/s4-echarts-vs-plotly.md`): ECharts 6 `common`, servido desde el sitio.
- ~~Tamaño real del Parquet en el repo (condiciona el plan B en R2).~~ Resuelto en S5 (`docs/spikes/s5-parquet-backfill.md`): ≈ 10 MB de backfill, ~3 MB/año; alcanza el repo, sin R2.

**Pendientes externos:** crear el proyecto en Cloudflare Pages y confirmar que `ecopy.pages.dev` está libre; crear el repo público en GitHub (el usuario `ecopy` está tomado).

**Nombre:** ecopy. Descartados PyScope (tomado en PyPI), "State of Python" (informe de JetBrains/PSF), ecopython (requiere permiso de marca de la PSF), pytonic.
