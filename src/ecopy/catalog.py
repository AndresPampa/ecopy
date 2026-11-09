"""Catálogo: librerías curadas, taxonomía y top 100 anual, validados al cargar."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Protocol

import yaml

FIRST_RANKED_YEAR = 2017
"""Primer año completo en la fuente (spike S1)."""

_HEADER = """\
# Generado por `ecopy catalog refresh`: no editar a mano.
# Los años cerrados quedan fijos; revisar por diff lo que entra en el año en curso.
"""


class CatalogError(Exception):
    """El catálogo no es válido; `problems` los lista todos."""

    def __init__(self, problems: Sequence[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = list(problems)


@dataclass(frozen=True)
class Library:
    project: str
    category: str
    tags: tuple[str, ...]
    repo: str | None
    renamed_from: str | None


@dataclass(frozen=True)
class Domain:
    slug: str
    categories: tuple[str, ...]


@dataclass(frozen=True)
class PythonRelease:
    version: str
    released: date
    end_of_life: date | None


class _TopSource(Protocol):
    def top_projects(self, years: Sequence[int], n: int = 100) -> Any: ...


def _read(path: Path, problems: list[str]) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        problems.append(f"falta el archivo {path.name}")
    except yaml.YAMLError as error:
        problems.append(f"{path.name} no es YAML válido: {error}")
    return None


def _check_entry(kind: str, entry: dict, seen: set[str], problems: list[str]) -> None:
    slug = entry.get("slug", "?")
    if slug in seen:
        problems.append(f"{kind} con slug duplicado: {slug}")
    seen.add(slug)
    for lang in ("en", "es"):
        if not entry.get(lang):
            problems.append(f"{kind} {slug}: falta la etiqueta {lang}")


def _read_taxonomy(
    data: dict, problems: list[str]
) -> tuple[dict[str, str], tuple[str, ...], dict[str, dict[str, str]], tuple[Domain, ...]]:
    """Devuelve categoría → dominio, los tags, las etiquetas por slug y el árbol, en orden."""
    labels: dict[str, dict[str, str]] = {}
    domains: set[str] = set()
    categories: set[str] = set()
    tags: set[str] = set()
    domain_of: dict[str, str] = {}
    for domain in data.get("domains", []):
        _check_entry("dominio", domain, domains, problems)
        labels[domain.get("slug", "?")] = {k: domain.get(k, "") for k in ("en", "es")}
        for category in domain.get("categories", []):
            _check_entry("categoría", category, categories, problems)
            domain_of[category["slug"]] = domain["slug"]
            labels[category["slug"]] = {k: category.get(k, "") for k in ("en", "es")}
    tree = tuple(
        Domain(d["slug"], tuple(c["slug"] for c in d.get("categories", [])))
        for d in data.get("domains", [])
    )
    vocabulary = []
    for tag in data.get("tags", []):
        _check_entry("tag", tag, tags, problems)
        labels[tag.get("slug", "?")] = {k: tag.get(k, "") for k in ("en", "es")}
        vocabulary.append(tag.get("slug", "?"))
    return domain_of, tuple(vocabulary), labels, tree


_REPO = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_][A-Za-z0-9._-]*")


def _read_repos(data: dict, projects: set[str], problems: list[str]) -> dict[str, str | None]:
    """Un valor por paquete del catálogo: `owner/name`, o None si se revisó y no tiene GitHub."""
    repos: dict[str, str | None] = data.get("repos") or {}
    problems.extend(f"{p}: falta en repos.yaml" for p in sorted(projects - set(repos)))
    problems.extend(f"{p}: está en repos.yaml sin catalogar" for p in sorted(set(repos) - projects))
    problems.extend(
        f"{p}: repo inválido {r!r}"
        for p, r in sorted(repos.items())
        if r is not None and not _REPO.fullmatch(r)
    )
    return repos


def _library(entry: dict, domain_of: dict, vocabulary: set, problems: list[str]) -> Library:
    project = entry["project"]
    if "repo" in entry:
        problems.append(f"{project}: el repo va en repos.yaml")
    category = entry.get("category")
    if category is None:
        problems.append(f"{project}: no tiene categoría")
    elif category not in domain_of:
        problems.append(f"{project}: categoría inexistente {category}")
    tags = tuple(entry.get("tags") or ())
    problems.extend(
        f"{project}: tag fuera del vocabulario {t}" for t in tags if t not in vocabulary
    )
    return Library(project, category, tags, None, entry.get("renamed_from"))


def _read_releases(data: dict, problems: list[str]) -> tuple[PythonRelease, ...]:
    releases: dict[str, PythonRelease] = {}
    for entry in data.get("releases", []):
        release = PythonRelease(entry["version"], entry["released"], entry.get("end_of_life"))
        if release.version in releases:
            problems.append(f"release de Python duplicado: {release.version}")
        if release.end_of_life and release.end_of_life < release.released:
            problems.append(f"release {release.version}: termina antes de empezar")
        releases[release.version] = release
    return tuple(sorted(releases.values(), key=lambda r: r.released))


class Catalog:
    def __init__(
        self,
        libraries: dict[str, Library],
        domain_of: dict[str, str],
        *,
        top: Mapping[int, Sequence[str]] | None = None,
        releases: Sequence[PythonRelease] = (),
        labels: Mapping[str, Mapping[str, str]] | None = None,
        domains: Sequence[Domain] = (),
        tags: Sequence[str] = (),
    ) -> None:
        self._libraries = libraries
        self._domain_of = domain_of
        self._top = top or {}
        self._releases = tuple(releases)
        self._labels = labels or {}
        self._domains = tuple(domains)
        self._tags = tuple(tags)
        self._renamed_to = {
            lib.renamed_from: lib.project for lib in libraries.values() if lib.renamed_from
        }
        self.projects = tuple(sorted(libraries))

    @classmethod
    def load(cls, root: Path) -> Catalog:
        """Lee `taxonomy.yaml`, `libraries.yaml` y `top100.yaml`; falla con todos los errores."""
        root = Path(root)
        problems: list[str] = []
        taxonomy = _read(root / "taxonomy.yaml", problems) or {}
        entries = _read(root / "libraries.yaml", problems) or []
        top = _read(root / "top100.yaml", problems) or {}
        releases = _read_releases(_read(root / "python_releases.yaml", problems) or {}, problems)
        domain_of, vocabulary, labels, domains = _read_taxonomy(taxonomy, problems)
        libraries: dict[str, Library] = {}
        for entry in entries:
            library = _library(entry, domain_of, set(vocabulary), problems)
            if library.project in libraries:
                problems.append(f"proyecto duplicado: {library.project}")
            libraries[library.project] = library
        problems.extend(
            f"{library.project}: renombre a un paquete fuera del catálogo {library.renamed_from}"
            for library in libraries.values()
            if library.renamed_from and library.renamed_from not in libraries
        )
        ranked = {project for names in top.get("years", {}).values() for project in names}
        problems.extend(
            f"{p}: está en el top 100 sin categorizar" for p in sorted(ranked - set(libraries))
        )
        repos = _read_repos(_read(root / "repos.yaml", problems) or {}, set(libraries), problems)
        if problems:
            raise CatalogError(problems)
        libraries = {p: replace(lib, repo=repos[p]) for p, lib in libraries.items()}
        ranking = {int(year): tuple(names) for year, names in top.get("years", {}).items()}
        return cls(
            libraries,
            domain_of,
            top=ranking,
            releases=releases,
            labels=labels,
            domains=domains,
            tags=vocabulary,
        )

    def library(self, project: str) -> Library:
        return self._libraries[project]

    def libraries(self) -> tuple[Library, ...]:
        return tuple(self._libraries[p] for p in self.projects)

    def domains(self) -> tuple[Domain, ...]:
        """Dominios con sus categorías, en el orden de la taxonomía."""
        return self._domains

    def tags(self) -> tuple[str, ...]:
        return self._tags

    def renamed_to(self, project: str) -> str | None:
        """El nombre nuevo de un paquete renombrado, si está en el catálogo."""
        return self._renamed_to.get(project)

    def repos(self) -> tuple[str, ...]:
        """Repos de GitHub del catálogo, sin repetir: varios paquetes pueden compartir uno."""
        return tuple(sorted({lib.repo for lib in self._libraries.values() if lib.repo}))

    def projects_of_repo(self, repo: str) -> tuple[str, ...]:
        return tuple(p for p in self.projects if self._libraries[p].repo == repo)

    def domain_of(self, category: str) -> str:
        return self._domain_of[category]

    def top(self, year: int) -> tuple[str, ...]:
        """El top 100 de todo PyPI de ese año, en orden; vacío si no está generado."""
        return tuple(self._top.get(year, ()))

    def python_releases(self) -> tuple[PythonRelease, ...]:
        """Versiones menores de CPython, de la más vieja a la más nueva."""
        return self._releases

    def labels(self) -> Mapping[str, Mapping[str, str]]:
        """Etiquetas EN/ES de dominios, categorías y tags, por slug."""
        return self._labels


def refresh_top100(root: Path, source: _TopSource, *, now: datetime) -> list[str]:
    """Actualiza `top100.yaml` y devuelve los paquetes del top que no estaban antes.

    Los años cerrados ya guardados no se vuelven a pedir: su ranking queda fijo.
    """
    path = Path(root) / "top100.yaml"
    years: dict[int, list[str]] = (
        yaml.safe_load(path.read_text(encoding="utf-8"))["years"] if path.exists() else {}
    )
    known = {project for names in years.values() for project in names}
    current = now.astimezone(UTC).year
    pending = [y for y in range(FIRST_RANKED_YEAR, current + 1) if y == current or y not in years]
    fetched = source.top_projects(pending, 100)
    years.update({year: list(names) for year, names in fetched.items()})
    text = yaml.safe_dump({"years": dict(sorted(years.items()))}, allow_unicode=True)
    path.write_text(_HEADER + text, encoding="utf-8")
    return sorted({p for names in years.values() for p in names} - known)
