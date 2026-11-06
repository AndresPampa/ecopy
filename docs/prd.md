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

- Una **vista anual** desde 2018: cuota de descargas por categoría (neutraliza la inflación por CI),
  movers, recién llegados, adopción de versiones de Python, línea de tiempo del lenguaje y volumen
  total con advertencia explícita.
- **Fichas de librerías** de un catálogo de ~500 paquetes con su historia de descargas.
- **Releases de Python** en una línea de tiempo.
- Un **comparador simple** entre librerías.
- Una página de **metodología** que explica fuentes, cálculos, sesgos y versiones metodológicas.
- **Estrellas de GitHub** si la Fase 0 confirma una fuente histórica viable.

Todo se genera en un pipeline diario sin servidor: GitHub Actions → ingesta Python → almacenamiento
append-only en Parquet → cálculo de métricas → render HTML → Cloudflare Pages.

## User Stories

### Lector: vista anual
1. Como lector, quiero elegir un año desde 2018, para ver cómo estaba el ecosistema ese año.
2. Como lector, quiero ver la cuota de descargas por categoría en un año, para comparar el peso relativo de áreas (web, datos, ML, testing…) sin que la inflación por CI distorsione.
3. Como lector, quiero ver los "movers" del año (mayores subidas y bajadas de posición/cuota), para detectar tendencias.
4. Como lector, quiero ver los recién llegados al top del año, para descubrir librerías emergentes.
5. Como lector, quiero ver la adopción de versiones de Python por año, para saber cuándo una versión se volvió mayoritaria (si la Fase 0 confirma el desglose).
6. Como lector, quiero ver una línea de tiempo del lenguaje (releases, fin de soporte), para contextualizar los cambios de adopción.
7. Como lector, quiero ver el volumen total de descargas con una advertencia visible, para no interpretarlo como crecimiento de usuarios reales.
8. Como lector, quiero que el año en curso se muestre como YTD comparado con el mismo período del año anterior, para no comparar un año parcial contra uno completo.
9. Como lector, quiero que los rankings de años cerrados no cambien entre visitas, para poder citarlos con confianza.
10. Como lector, quiero ver qué versión metodológica produjo cada ranking anual, para entender por qué dos años podrían no ser comparables.
11. Como lector, quiero que no haya un "puntaje combinado" opaco, para interpretar cada métrica por separado.

### Lector: librerías
12. Como lector, quiero buscar/navegar el catálogo de librerías por categoría, para encontrar las de mi área.
13. Como lector, quiero una ficha por librería con su serie histórica de descargas, para ver su trayectoria desde 2018.
14. Como lector, quiero ver sparklines en listados, para comparar trayectorias de un vistazo.
15. Como lector, quiero ver que una librería renombrada enlaza con su nombre anterior, para seguir su historia completa.
16. Como lector, quiero que los renombres no se sumen automáticamente, para no ver cifras infladas o mezcladas.
17. Como lector, quiero ver las estrellas de GitHub de una librería (si están disponibles), para tener una señal complementaria a las descargas.
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
32. Como mantenedor, quiero un backfill único desde 2018 vía ClickPy, para tener el histórico sin pagar BigQuery.
33. Como mantenedor, quiero poder reconstruir el histórico desde BigQuery como respaldo, para no depender de un único proveedor.
34. Como mantenedor, quiero que cada fila guardada tenga procedencia (`source`, `acquisition=backfill|observed`, `captured_at`, `ingestion_run_id`), para auditar cualquier cifra.
35. Como mantenedor, quiero que el almacenamiento sea append-only, para que una corrida mala nunca destruya datos previos.
36. Como mantenedor, quiero que las correcciones de la fuente se registren como archivos nuevos, para conservar lo observado originalmente.
37. Como mantenedor, quiero que las métricas se recalculen en cada build desde los datos normalizados, para que un cambio de fórmula se aplique sin migraciones.
38. Como mantenedor, quiero guardar snapshots diarios de estrellas de GitHub desde el día 1, para no perder un dato que no se puede recuperar después.
39. Como mantenedor, quiero definir el catálogo curado por categoría en YAML, para editarlo sin tocar código.
40. Como mantenedor, quiero que el catálogo se complete automáticamente con la unión del top 100 de cada año, para no depender solo de mi criterio.
41. Como mantenedor, quiero declarar renombres en el catálogo, para enlazar historias sin sumarlas.
42. Como mantenedor, quiero que, si la validación falla, se publique el sitio del día anterior con el aviso de fallo, para nunca publicar datos rotos.
43. Como mantenedor, quiero un CLI con comandos separados (ingestar, construir, validar), para correr cada etapa localmente.
44. Como mantenedor, quiero consultar ClickPy con moderación (límite de ritmo), para ser un buen ciudadano de un servicio gratuito.
45. Como mantenedor, quiero que las opciones de gráficos se generen desde modelos tipados, para detectar errores al construir y no en el navegador.

### Seguridad y privacidad
46. Como usuario de GitHub, quiero que ecopy nunca persista identidades de usuarios (solo conteos), para que mi actividad no quede expuesta.
47. Como lector, quiero que el sitio no ejecute contenido externo inyectado, para estar a salvo de XSS (autoescape, sin `|safe` en campos externos, sin Markdown externo, solo URLs https, CSP estricta).
48. Como mantenedor, quiero Actions fijadas por SHA, permisos mínimos por job y sin `pull_request_target`, para reducir el riesgo de supply chain.

## Implementation Decisions

**Arquitectura**
- Sitio 100 % pre-generado; sin servidor en runtime. Evidencia: los datos cambian 1×/día y todo es de lectura → costo cero, CDN, SEO, menor superficie de ataque. FastAPI queda reservado para una futura API pública; Supabase para Fase 4 (auth/encuestas), porque su free tier de 500 MB no alcanza para el histórico diario.
- Pipeline: GitHub Actions (cron diario, repo público bajo la cuenta del usuario) → ingesta → normalización → métricas → render → deploy a Cloudflare Pages (`ecopy.pages.dev`, sin dominio pago).

**Módulos** (profundos, con interfaces pequeñas; `site` nunca toca `store`)
- `sources` — adaptadores por proveedor (ClickPy, BigQuery de respaldo, releases de Python, GitHub). Entrada: rango de fechas/paquetes. Salida: registros tipados con procedencia. Toda la E/S HTTP pasa por un cliente `httpx` inyectable.
- `store` — escritura append-only de Parquet particionado (`raw` → `normalized`) y lectura vía DuckDB. Nunca sobrescribe; una corrección es un archivo nuevo. Expone una vista de solo lectura del dataset normalizado.
- `catalog` — carga el YAML curado, calcula la unión de top-100 anuales, resuelve categorías y renombres (enlaces, no sumas).
- `metrics` — funciones puras sobre el dataset normalizado + catálogo: cuota por categoría, movers, recién llegados, adopción de versiones, YTD vs mismo período, rankings anuales congelados con versión metodológica. Sin puntaje combinado.
- `site` — recibe únicamente modelos de vista (Pydantic) producidos por `metrics`; renderiza Jinja2 (autoescape) + opciones de ECharts serializadas desde Pydantic + sparklines SVG generadas en Python; i18n EN/ES; emite `_headers` con CSP.
- `cli` — orquesta: `ingest`, `backfill`, `validate`, `build`. Decide publicar el build del día anterior con estado "Actualización fallida" si `validate` falla.

**Datos**
- Esquema de procedencia por fila: `source`, `acquisition` (`backfill` | `observed`), `captured_at`, `ingestion_run_id`.
- Particionado por fuente y fecha dentro del repo. Git LFS descartado; Cloudflare R2 como plan B si el tamaño o los términos de ClickPy lo exigen.
- Año calendario en UTC. Rankings de años cerrados se congelan junto con su versión metodológica.
- Estrellas de GitHub: se guardan solo conteos diarios; nunca logins ni IDs de usuarios.

**Fuentes**
- ClickPy (usuario `play`, gratis) como fuente principal del backfill desde 2018 (antes si es gratis). Sin solicitar permiso: el dato es público (PyPI/linehaul); se atribuye y se limita el ritmo.
- BigQuery (`pypi` público) solo como respaldo reproducible, porque cobra por bytes escaneados.

**Frontend**
- Python-first: Jinja2 + ECharts + SVG. Descartados Dash/Streamlit/Reflex/NiceGUI (requieren servidor) y PyScript (peso). ECharts vs Plotly se decide en un prototipo de Fase 0.
- Diseño guiado por los skills `impeccable` y `dataviz`.

## Testing Decisions

**Qué es un buen test aquí:** verifica comportamiento observable en un seam público (registros devueltos, archivos escritos, HTML generado), nunca detalles internos (nombres de funciones privadas, consultas SQL exactas, estructura interna de DataFrames).

**Seams acordados (de más alto a más bajo):**
1. **CLI end-to-end (humo):** `ingest` + `build` sobre fixtures HTTP grabadas → directorio de sitio generado. Se afirma: páginas clave existen en EN/ES, contienen cifras esperadas, `_headers` trae la CSP, y con validación fallida se publica el build anterior con el aviso.
2. **`sources` (contrato):** cada adaptador contra respuestas fijas vía `httpx.MockTransport`; se afirma el mapeo a registros tipados con procedencia y el manejo de errores/rate limit. Sin red real en CI.
3. **`store` (inmutabilidad):** sobre un directorio temporal; escribir dos veces o escribir una corrección nunca modifica archivos existentes; la lectura refleja la última corrección.
4. **`metrics` (unitarios puros + propiedades con Hypothesis):** p. ej., las cuotas por categoría suman 1; los rankings congelados no cambian al agregar datos posteriores; los renombres nunca se suman; YTD compara ventanas de igual longitud.
5. **`site` (snapshots):** modelos de vista fijos → HTML/opciones ECharts comparados con snapshots; tests de que campos externos con `<script>` salen escapados.

`catalog` se cubre con unitarios puros (YAML de ejemplo → categorías, unión de top-100, renombres).

**Prior art:** no hay código del producto aún. El único antecedente en el repo son los tests de hooks del tooling (script Python plano, sin pytest), que no aplican como patrón; el proyecto adoptará `pytest` + `hypothesis`.

## Out of Scope

- Trending y Seguridad (Fase 3). Solo se adelanta la captura diaria de estrellas.
- Autenticación, cuentas, encuestas (Fase 4, Supabase).
- API pública (FastAPI, futura).
- Dominio propio pago.
- Publicar en PyPI.
- Puntajes combinados o "índices de popularidad" que mezclen métricas.
- Cualquier dato de identidad de usuarios de GitHub.
- Estrellas históricas de GitHub si la Fase 0 no confirma una fuente viable.

## Further Notes

**Fase 0 (spikes que condicionan este PRD):**
- Cobertura de años y calidad del dato antiguo en ClickPy.
- Si ClickPy desglosa por versión de Python (condiciona la historia 5).
- Fuente de histórico de estrellas: verificar si existe un endpoint de historia; la alternativa conocida es reconstruir desde `starred_at` del listado de stargazers, con el riesgo de paginación/límites en repos grandes (condiciona la historia 17).
- Peso real de ECharts vs Plotly en un prototipo de ranking + ficha.
- Tamaño real del Parquet en el repo (condiciona el plan B en R2).

**Pendientes externos:** crear el proyecto en Cloudflare Pages y confirmar que `ecopy.pages.dev` está libre; crear el repo público en GitHub (el usuario `ecopy` está tomado).

**Nombre:** ecopy. Descartados PyScope (tomado en PyPI), "State of Python" (informe de JetBrains/PSF), ecopython (requiere permiso de marca de la PSF), pytonic.
