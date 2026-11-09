# Spike S8 — Repos de GitHub y tags del catálogo

> Fecha: 2026-11-09 · Script: `uv run docs/spikes/s8_repos_y_tags.py` (500 consultas a PyPI)

## Pregunta

¿De dónde sale el `repo` de las 500 librerías y cuánto se pueden ampliar los tags con datos públicos?

## Resultados

- **PyPI:** 462 de 500 tienen una URL de GitHub. ClickPy (`pypi.project_to_repo_name`) coincide en 323
  de 407, y suele tener dueños viejos o restos como `#history`.
- **Muestra de 42 repos** (`GET /repos/{o}/{r}`, sin token): todos existen, ninguno redirige, uno
  archivado. Media de 581 semanas y 19,8 páginas de historia.
- **Resultado:** `catalog/repos.yaml` con 486 repos (459 únicos) y 14 paquetes en `null`.
- **Tags:** 13 en el vocabulario y 176 librerías con al menos uno (110 sin contar `typed`).

## Qué revisar a mano

- **Corregidos a mano en `CORRECTIONS`**, porque PyPI era ambiguo o erróneo: `ansible`, `lightning`,
  `pytorch-lightning`, `poetry-core`, `rdkit`, `rpds-py`, `types-pyyaml`, `types-requests` y
  `typing-extensions`.
- **Sin URL en PyPI, completados de memoria y sin verificar** (`NO_METADATA` en el script): 24
  repos y 14 `null`. `ecopy stars` informa los que falten o se hayan movido.
- **Reglas de tags:** `jupyter` excluye a mano `rich`, `tqdm`, `progressbar2` y `scalene`.

## Límites

La muestra prueba que el repo existe, no que sea el correcto del paquete. Las keywords de PyPI no
se usan: solo 205 de 500 las tienen y son ruidosas.
