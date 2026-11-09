"""Catálogo: YAML de ejemplo → librerías, categorías, validaciones y top 100."""

from datetime import UTC, datetime

import pytest
import yaml

from ecopy.catalog import Catalog, CatalogError, refresh_top100

TAXONOMY = {
    "domains": [
        {
            "slug": "development",
            "en": "Development",
            "es": "Desarrollo",
            "categories": [
                {"slug": "web", "en": "Web", "es": "Web"},
                {"slug": "testing", "en": "Testing", "es": "Testing"},
            ],
        }
    ],
    "tags": [{"slug": "async", "en": "Async", "es": "Asíncrono"}],
}
LIBRARIES = [
    {"project": "fastapi", "category": "web", "tags": ["async"], "repo": "fastapi/fastapi"},
    {"project": "pytest", "category": "testing"},
]
TOP = {"years": {2024: ["fastapi"]}}


def write(root, *, taxonomy=TAXONOMY, libraries=LIBRARIES, top=TOP):
    root.mkdir(exist_ok=True)
    (root / "taxonomy.yaml").write_text(yaml.safe_dump(taxonomy, allow_unicode=True))
    (root / "libraries.yaml").write_text(yaml.safe_dump(libraries, allow_unicode=True))
    (root / "top100.yaml").write_text(yaml.safe_dump(top))
    return root


def problems(root) -> str:
    with pytest.raises(CatalogError) as error:
        Catalog.load(root)
    return "\n".join(error.value.problems)


def test_loads_libraries_with_their_category_and_domain(tmp_path):
    catalog = Catalog.load(write(tmp_path / "c"))

    assert catalog.projects == ("fastapi", "pytest")
    library = catalog.library("fastapi")
    assert (library.category, library.tags, library.repo) == ("web", ("async",), "fastapi/fastapi")
    assert catalog.domain_of("testing") == "development"


def test_tags_repo_and_rename_are_optional(tmp_path):
    library = Catalog.load(write(tmp_path / "c")).library("pytest")

    assert (library.tags, library.repo, library.renamed_from) == ((), None, None)


def test_an_unknown_category_is_rejected(tmp_path):
    root = write(tmp_path / "c", libraries=[{"project": "fastapi", "category": "nope"}])

    assert "nope" in problems(root)


def test_a_tag_outside_the_vocabulary_is_rejected(tmp_path):
    libraries = [{"project": "fastapi", "category": "web", "tags": ["ml"]}]

    assert "ml" in problems(write(tmp_path / "c", libraries=libraries))


def test_a_duplicated_project_is_rejected(tmp_path):
    libraries = [{"project": "fastapi", "category": "web"}] * 2

    assert "duplicado" in problems(write(tmp_path / "c", libraries=libraries))


def test_a_library_needs_a_category(tmp_path):
    assert "fastapi" in problems(write(tmp_path / "c", libraries=[{"project": "fastapi"}]))


def test_a_rename_must_point_to_a_project_of_the_catalog(tmp_path):
    libraries = [{"project": "fastapi", "category": "web", "renamed_from": "starlite"}]

    assert "starlite" in problems(write(tmp_path / "c", libraries=libraries))


def test_a_valid_rename_is_a_link_between_two_libraries(tmp_path):
    libraries = [
        {"project": "pypdf", "category": "web", "renamed_from": "pypdf2"},
        {"project": "pypdf2", "category": "web"},
    ]
    catalog = Catalog.load(write(tmp_path / "c", libraries=libraries, top={"years": {}}))

    assert catalog.library("pypdf").renamed_from == "pypdf2"


def test_every_top_project_must_be_categorized(tmp_path):
    root = write(tmp_path / "c", top={"years": {2024: ["urllib3"]}})

    assert "urllib3" in problems(root)


def test_all_problems_are_reported_together(tmp_path):
    libraries = [
        {"project": "a", "category": "nope"},
        {"project": "b", "category": "web", "tags": ["ml"]},
    ]

    text = problems(write(tmp_path / "c", libraries=libraries, top={"years": {}}))

    assert "nope" in text and "ml" in text


def test_a_duplicated_slug_in_the_taxonomy_is_rejected(tmp_path):
    taxonomy = {
        "domains": [
            {
                "slug": "d",
                "en": "D",
                "es": "D",
                "categories": [
                    {"slug": "web", "en": "A", "es": "A"},
                    {"slug": "web", "en": "B", "es": "B"},
                ],
            }
        ],
        "tags": [],
    }

    assert "web" in problems(
        write(tmp_path / "c", taxonomy=taxonomy, libraries=[], top={"years": {}})
    )


def test_a_label_is_required_in_both_languages(tmp_path):
    taxonomy = {"domains": [{"slug": "d", "en": "D", "categories": []}], "tags": []}

    assert "es" in problems(
        write(tmp_path / "c", taxonomy=taxonomy, libraries=[], top={"years": {}})
    )


def test_a_missing_file_is_reported(tmp_path):
    root = write(tmp_path / "c")
    (root / "top100.yaml").unlink()

    assert "top100.yaml" in problems(root)


class FakeTop:
    def __init__(self) -> None:
        self.asked: list[list[int]] = []

    def top_projects(self, years, n=100):
        self.asked.append(list(years))
        return {year: (f"new{year}", "fastapi") for year in years}


NOW = datetime(2026, 11, 9, tzinfo=UTC)


def test_refresh_keeps_closed_years_and_rereads_the_current_one(tmp_path):
    root = tmp_path / "c"
    root.mkdir()
    closed = {year: ["old"] for year in range(2017, 2026)}
    (root / "top100.yaml").write_text(yaml.safe_dump({"years": {**closed, 2026: ["stale"]}}))
    source = FakeTop()

    added = refresh_top100(root, source, now=NOW)

    assert source.asked == [[2026]]
    saved = yaml.safe_load((root / "top100.yaml").read_text())["years"]
    assert saved[2017] == ["old"]
    assert saved[2026] == ["new2026", "fastapi"]
    assert added == ["fastapi", "new2026"]


def test_first_refresh_reads_every_year_since_2017(tmp_path):
    root = tmp_path / "c"
    root.mkdir()
    source = FakeTop()

    refresh_top100(root, source, now=NOW)

    assert source.asked == [list(range(2017, 2027))]
