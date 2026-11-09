# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx", "pyyaml"]
# ///
"""S8: borrador de `catalog/repos.yaml` y de los tags, desde la metadata pública de PyPI.

Uso: `uv run docs/spikes/s8_repos_y_tags.py [--cache archivo.json]`. Se corre una vez; después el
catálogo se mantiene a mano. Informe y decisiones: `docs/spikes/s8-repos-y-tags.md`.
"""

import argparse
import json
import re
import time
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "catalog"
GITHUB = re.compile(
    r"https?://(?:www\.)?github\.com/([A-Za-z0-9][\w.-]*)/([\w.-]+?)(?:\.git)?(?:[/#?].*)?$", re.I
)
NOT_OWNERS = {"sponsors", "orgs", "apps", "marketplace", "features", "site", "about"}
PRIORITY = ["source", "source code", "sourcecode", "repository", "code", "github", "homepage"]

# Revisión manual: paquetes con candidatos ambiguos o erróneos en PyPI.
CORRECTIONS = {
    "ansible": "ansible/ansible",
    "lightning": "Lightning-AI/pytorch-lightning",
    "pytorch-lightning": "Lightning-AI/pytorch-lightning",
    "poetry-core": "python-poetry/poetry-core",
    "rdkit": "rdkit/rdkit",
    "rpds-py": "crate-py/rpds",
    "types-pyyaml": "python/typeshed",
    "types-requests": "python/typeshed",
    "typing-extensions": "python/typing_extensions",
}
# Sin URL de GitHub en PyPI. De memoria y sin verificar contra la API: `ecopy stars` informa los
# que no existan o estén movidos. `None` = el proyecto se aloja fuera de GitHub o no tiene repo.
NO_METADATA = {
    "apache-beam": "apache/beam",
    "awscli-cwlogs": None,
    "backports-ssl-match-hostname": None,
    "beautifulsoup4": None,
    "databricks-sdk": "databricks/databricks-sdk-py",
    "decorator": "micheles/decorator",
    "docopt": "docopt/docopt",
    "docutils": None,
    "enum34": None,
    "et-xmlfile": None,
    "funcsigs": "testing-cabal/funcsigs",
    "grpcio-status": "grpc/grpc",
    "ipywidgets": "jupyter-widgets/ipywidgets",
    "moviepy": "Zulko/moviepy",
    "msgpack-python": "msgpack/msgpack-python",
    "nbconvert": "jupyter/nbconvert",
    "nose": "nose-devs/nose",
    "numba": "numba/numba",
    "openpyxl": None,
    "passlib": None,
    "pbr": None,
    "pep8": "PyCQA/pycodestyle",
    "protobuf": "protocolbuffers/protobuf",
    "py": "pytest-dev/py",
    "py4j": "py4j/py4j",
    "pycodestyle": "PyCQA/pycodestyle",
    "pycrypto": "pycrypto/pycrypto",
    "pydub": "jiaaro/pydub",
    "pyqt5": None,
    "pyqt6": None,
    "pyside6": None,
    "python-socketio": "miguelgrinberg/python-socketio",
    "quantlib": "lballabio/QuantLib",
    "reportlab": None,
    "ruamel-yaml": None,
    "selenium": "SeleniumHQ/selenium",
    "sortedcontainers": "grantjenks/python-sortedcontainers",
    "xlrd": "python-excel/xlrd",
}
NOT_JUPYTER = {"rich", "tqdm", "progressbar2", "scalene"}


def tags_of(project: str, classifiers: list[str]) -> set[str]:
    found = set()
    if "Typing :: Typed" in classifiers or project.startswith("types-"):
        found.add("typed")
    asyncio = ("Framework :: AsyncIO", "Framework :: Trio", "Framework :: AnyIO")
    if any(c in classifiers for c in asyncio) or project.startswith(("aio", "async")):
        found.add("async")
    if project.startswith("django") or any(c.startswith("Framework :: Django") for c in classifiers):
        found.add("django")
    if project not in NOT_JUPYTER and (
        project.startswith(("jupyter", "ipy", "nb"))
        or "Framework :: Jupyter" in classifiers
        or "Framework :: IPython" in classifiers
    ):
        found.add("jupyter")
    if project.startswith("pytest") or "Framework :: Pytest" in classifiers:
        found.add("pytest")
    return found


def candidate(info: dict) -> str | None:
    urls = dict(info.get("project_urls") or {})
    if info.get("home_page"):
        urls.setdefault("home_page", info["home_page"])
    rank = lambda kv: PRIORITY.index(kv[0].lower()) if kv[0].lower() in PRIORITY else 50
    for _, url in sorted(urls.items(), key=rank):
        match = GITHUB.match((url or "").strip())
        if match and match[1].lower() not in NOT_OWNERS and match[2] != ".github":
            return f"{match[1]}/{match[2]}"
    return None


def fetch(projects: list[str]) -> dict:
    found = {}
    with httpx.Client(timeout=30, headers={"User-Agent": "ecopy-catalog-research"}) as client:
        for project in projects:
            response = client.get(f"https://pypi.org/pypi/{project}/json")
            response.raise_for_status()
            found[project] = response.json()["info"]
            time.sleep(0.1)
    return found


def rewrite_entries(text: str, change) -> str:
    """Reescribe solo las entradas que `change` modifica, en el estilo de bloque del archivo."""
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        if not lines[i].startswith("- "):
            out.append(lines[i])
            i += 1
            continue
        j = i + 1
        while j < len(lines) and lines[j].startswith("  "):
            j += 1
        block = lines[i:j]
        entry = yaml.safe_load("\n".join(block))[0]
        updated = change(dict(entry))
        if updated == entry:
            out.extend(block)
        else:
            out.append(f"- project: {updated['project']}")
            out.append(f"  category: {updated['category']}")
            if updated.get("tags"):
                out.append(f"  tags: [{', '.join(updated['tags'])}]")
            if updated.get("renamed_from"):
                out.append(f"  renamed_from: {updated['renamed_from']}")
        i = j
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path)
    args = parser.parse_args()
    libraries_path = CATALOG / "libraries.yaml"
    text = libraries_path.read_text(encoding="utf-8")
    projects = [e["project"] for e in yaml.safe_load(text)]
    info = json.loads(args.cache.read_text()) if args.cache else fetch(projects)

    repos = {}
    for project in projects:
        repos[project] = CORRECTIONS.get(project) or candidate(info[project])
        if repos[project] is None:
            repos[project] = NO_METADATA.get(project)
            if project not in NO_METADATA:
                print(f"SIN REVISAR: {project}")
    header = (
        "# Repo de GitHub de cada paquete (`owner/name`). `null` = revisado, sin repo en GitHub.\n"
        "# Borrador generado por docs/spikes/s8_repos_y_tags.py; se mantiene a mano.\n"
    )
    body = yaml.safe_dump({"repos": repos}, allow_unicode=True, sort_keys=True)
    (CATALOG / "repos.yaml").write_text(header + body, encoding="utf-8")

    def with_tags(entry: dict) -> dict:
        classifiers = info[entry["project"]].get("classifiers") or []
        existing = entry.get("tags") or []
        new = sorted(tags_of(entry["project"], classifiers) - set(existing))
        if new:
            entry["tags"] = [*existing, *new]
        return entry

    libraries_path.write_text(rewrite_entries(text, with_tags), encoding="utf-8")
    print(f"{sum(1 for r in repos.values() if r)} con repo, {len(set(repos.values()) - {None})} únicos")


if __name__ == "__main__":
    main()
