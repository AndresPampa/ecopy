# Spike S3 — Fuente del histórico de estrellas de GitHub

> Fecha: 2026-11-06 · Script: `uv run docs/spikes/s3_github_stars.py` (~12 consultas, sin token)

## Pregunta

¿Hay una fuente viable del histórico de estrellas por repo? ¿Cuánto cuesta para ~500 repos y
cómo se mapea un paquete de PyPI a su repo?

## Método

- API REST de GitHub sin autenticación (60 consultas/hora por IP).
- `GET /repos/{o}/{r}/stargazers/history` sobre un repo joven completo (`astral-sh/uv`) y la primera
  y última página de uno viejo (`psf/requests`); comparación con `stargazers_count`.
- Alternativa: `GET /repos/{o}/{r}/stargazers` con `application/vnd.github.star+json` (`starred_at`).
- Documentación: <https://docs.github.com/en/rest/activity/starring>.
- Mapeo paquete → repo: tabla `pypi.project_to_repo_name` de ClickPy.

## Resultados

**El endpoint de historia existe y está documentado** (no marcado como preview/beta).
Corrige la suposición previa del handoff de que "probablemente no existe".

- Devuelve estrellas agrupadas por semana calendario, **más reciente primero**:
  `{"week": <epoch domingo>, "total": 160, "days": [13, 10, 11, 10, 28, 88, 0]}` (por día, desde domingo).
- 30 semanas por página (`per_page` máx. 30; se ignoran valores mayores); `page` máx. 100
  (= 3.000 semanas ≈ 57 años: alcanza para cualquier repo). Las semanas sin estrellas vienen en 0.
- **Cuadra exacto:** `astral-sh/uv`, 6 páginas, 162 semanas (2023-10-01 → 2026-11-01): suma de
  semanas = suma de días = `stargazers_count` = 91.713. Sin valores negativos.
- Es un conteo **neto**: refleja a quienes tienen la estrella hoy, fechada cuando la dieron. Si
  alguien la quita, desaparece de su semana original (la historia puede bajar levemente).
- Artefacto en repos viejos: `psf/requests` acumula 2.611 estrellas en su semana de creación
  (2011-02-13) frente a ~30 las siguientes; probablemente estrellas sin fecha real (anteriores al
  registro de fechas o de antes de una transferencia). Se marca, no se corrige.

**La alternativa con `starred_at` ya no sirve:** el listado de stargazers responde
`401 Requires authentication`, y la documentación indica que desde julio de 2026 se limita a admins
y colaboradores del repo. Además expone identidades, que no queremos tocar.

**Costo** (páginas = semanas de vida del repo / 30):
| Uso | Consultas | Con qué |
|---|---|---|
| Backfill de un repo de 15 años | ~27 | |
| Backfill de ~500 repos (edad media supuesta ~10 años) | ~9.000, una sola vez | `GITHUB_TOKEN` de Actions, repartido en varias corridas |
| Actualización (página 1 = últimas 30 semanas, con días) | 1 por repo → ~500 por corrida | `GITHUB_TOKEN` de Actions |

Sin token (60/h) el backfill tomaría ~150 h: no es viable. El `GITHUB_TOKEN` que Actions da a cada
corrida es gratis; su cuota (1.000 consultas/hora por repo, según la documentación de GitHub; no
verificado en este spike) alcanza para la actualización y para el backfill repartido en ~10 días.

**Mapeo paquete → repo:** `pypi.project_to_repo_name` (ClickPy) existe pero está incompleto y
desactualizado: `requests → kennethreitz/requests` (hoy `psf/requests`), `fastapi →
tiangolo/fastapi` (hoy `fastapi/fastapi`), sin `django` ni `beautifulsoup4`. GitHub redirige los
repos renombrados, pero el repo canónico debe declararse en el catálogo.

## Decisión (confirmada por el usuario el 2026-11-07)

1. **Historia 17 confirmada:** estrellas por repo vía `stargazers/history`, con `GITHUB_TOKEN`.
2. **Ya no hace falta guardar snapshots diarios "porque no se recuperan":** la historia se recupera
   cuando se quiera. Se ingesta la página 1 en cada corrida (append-only, como el resto) y se
   guarda además `stargazers_count` del día, que es barato y conserva el valor bruto.
3. Backfill de estrellas en la Etapa 4, repartido en varias corridas para no agotar la cuota.
4. El catálogo YAML declara el repo de cada paquete (`owner/name`); la tabla de ClickPy solo como
   sugerencia inicial. Paquetes sin repo en GitHub (p. ej. `beautifulsoup4`) no muestran estrellas.
5. Metodología: estrellas netas, artefacto de la semana de creación, nunca identidades.

## Abierto

- Verificar la cuota real del `GITHUB_TOKEN` en la primera corrida de Actions (Etapa 1).
- Medir la edad real de los repos del catálogo cuando exista (afina el costo del backfill).
