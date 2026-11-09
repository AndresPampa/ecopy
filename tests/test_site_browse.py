"""Páginas de navegación: catálogo, dominios, categorías, comparador, releases y ficha ampliada."""

import json
import re
from datetime import date
from html.parser import HTMLParser

import pytest

from ecopy.models import (
    BrowseView,
    CategoryPage,
    CategoryShare,
    Coverage,
    DomainPage,
    DomainShare,
    LibraryRow,
    LibraryView,
    MonthPoint,
    Mover,
    ReleaseRow,
    ReleasesView,
    StarPoint,
    StarsView,
    VolumeView,
    YearShare,
    YearView,
)
from ecopy.site import render_site, svg

FULL = Coverage(expected=31, gap=0, degraded=0)
LABELS = {
    "development": {"en": "Development", "es": "Desarrollo"},
    "web": {"en": "Web development", "es": "Desarrollo web"},
    "async": {"en": "Async", "es": "Asíncrono"},
}


def row(project="fastapi", downloads=1_000, **changes) -> LibraryRow:
    base = {
        "project": project,
        "category": "web",
        "domain": "development",
        "tags": ("async",),
        "month": date(2024, 3, 1),
        "downloads": downloads,
        "trend": (0.1, 0.2, 0.3),
    }
    return LibraryRow(**{**base, **changes})


def browse(*rows) -> BrowseView:
    rows = rows or (row(),)
    shares = (
        YearShare(year=2023, status="closed", share=0.5),
        YearShare(year=2024, status="ytd", share=0.75),
    )
    category = CategoryPage(slug="web", domain="development", shares=shares, rows=rows)
    domain = DomainPage(slug="development", shares=shares, categories=(category,))
    releases = ReleasesView(
        as_of=date(2026, 11, 8),
        releases=(
            ReleaseRow(
                version="3.13",
                released=date(2024, 10, 7),
                end_of_life=date(2029, 10, 31),
                status="supported",
            ),
            ReleaseRow(
                version="3.8",
                released=date(2019, 10, 14),
                end_of_life=date(2024, 10, 7),
                status="end_of_life",
            ),
            ReleaseRow(
                version="2.5", released=date(2006, 9, 19), end_of_life=None, status="unknown"
            ),
        ),
    )
    return BrowseView(rows=rows, domains=(domain,), releases=releases, tags=("async",))


def view(project="fastapi", **changes) -> LibraryView:
    months = (
        MonthPoint(
            month=date(2024, 2, 1), downloads=40, status="complete", coverage=FULL, share=0.04
        ),
        MonthPoint(month=date(2024, 3, 1), downloads=None, status="complete", coverage=FULL),
        MonthPoint(
            month=date(2024, 4, 1), downloads=5, status="in_progress", coverage=FULL, share=0.01
        ),
    )
    base = {
        "project": project,
        "first_date": date(2024, 2, 1),
        "last_closed_month": months[0],
        "monthly": months,
        "yearly": (),
        "category": "web",
        "domain": "development",
        "tags": ("async",),
        "repo": "fastapi/fastapi",
    }
    return LibraryView(**{**base, **changes})


def year(number=2024) -> YearView:
    mover = Mover(
        project="fastapi", category="web", share=0.2, share_change=1.25, rank=3, rank_change=2
    )
    return YearView(
        year=number,
        status="closed",
        methodology_version=1,
        period_start=date(number, 1, 1),
        period_end=date(number, 12, 31),
        previous_start=None,
        previous_end=None,
        coverage=Coverage(expected=366, gap=0, degraded=0),
        volume=VolumeView(total=9, previous=None, growth=None, discontinuities=()),
        catalog_share=0.5,
        domains=(
            DomainShare(
                slug="development",
                downloads=1,
                share=1.0,
                categories=(CategoryShare(slug="web", downloads=1, share=1.0),),
            ),
        ),
        movers_up=(mover,),
        movers_down=(),
        newcomers=(),
        python_versions=(),
        python_unknown_share=0.0,
        python_other_share=0.0,
        timeline=(),
    )


def build(out, pages=None, data=None, years=None):
    render_site(
        [view()] if pages is None else pages,
        out,
        years=(year(),) if years is None else years,
        labels=LABELS,
        browse=data or browse(),
    )


def read(out, path, lang="en") -> str:
    return (out / lang / path / "index.html").read_text()


def test_navigation_reaches_the_new_sections(tmp_path):
    build(tmp_path)

    html = read(tmp_path, "library")

    assert 'href="/en/library/" aria-current="page">Libraries' in html
    assert 'href="/en/compare/"' in html and 'href="/en/python/"' in html


def test_the_catalog_lists_each_library_with_its_figures_and_trend(tmp_path):
    build(tmp_path)

    english, spanish = read(tmp_path, "library"), read(tmp_path, "library", "es")

    assert 'href="/en/library/fastapi/"' in english
    assert "1,000" in english and "1.000" in spanish
    assert '<polyline points="' in english
    assert "Web development" in english and "Desarrollo web" in spanish


def test_a_row_without_enough_history_has_no_sparkline(tmp_path):
    build(tmp_path, data=browse(row(trend=(0.1,))))

    assert "<polyline" not in read(tmp_path, "library")


def test_rows_and_controls_are_ready_for_the_tag_filter(tmp_path):
    build(tmp_path, data=browse(row(tags=("async", "typed"))))

    html = read(tmp_path, "library")

    assert 'data-tags="async typed"' in html
    assert 'data-tag="async"' in html and "Async" in html
    assert '<script src="/static/filter.js" defer>' in html


def test_domain_and_category_pages_show_share_per_year_and_their_libraries(tmp_path):
    build(tmp_path)

    domain, category = read(tmp_path, "domain/development"), read(tmp_path, "category/web")

    assert "<h1>Development</h1>" in domain and 'href="/en/category/web/"' in domain
    assert "<h1>Web development</h1>" in category and 'href="/en/domain/development/"' in category
    assert 'href="/en/library/fastapi/"' in category
    payload = json.loads(re.search(r'id="chart-share-data"[^>]*>(.*?)</script>', category, re.S)[1])
    assert payload["option"]["series"][0]["data"][0] == {"value": 50.0}
    assert payload["option"]["xAxis"]["data"] == ["2023", "2024 YTD"]


def test_the_python_page_lists_versions_with_their_support_status(tmp_path):
    build(tmp_path)

    english, spanish = read(tmp_path, "python"), read(tmp_path, "python", "es")

    assert "3.13" in english and "2029-10-31" in english
    assert "Supported" in english and "End of life" in english and "Not published" in english
    assert "Con soporte" in spanish and "Sin soporte" in spanish
    assert english.count('class="bar') == 2


def test_a_year_label_never_collides_with_today_on_the_lifecycle():
    releases = ReleasesView(
        as_of=date(2028, 1, 2),
        releases=(
            ReleaseRow(
                version="3.8",
                released=date(2019, 1, 1),
                end_of_life=date(2031, 1, 1),
                status="supported",
            ),
        ),
    )

    drawn = svg.lifecycle(releases)

    assert all(abs(x - drawn.today_x) > 48 for _, x in drawn.ticks)
    assert drawn.ticks


def test_the_compare_page_has_its_controls_and_script(tmp_path):
    build(tmp_path)

    html = read(tmp_path, "compare")

    assert 'id="compare-chart"' in html and 'id="compare-table"' in html
    assert '<script src="/static/compare.js" defer>' in html
    assert "<noscript>" in html
    assert "<form" not in html


def test_compare_data_has_only_closed_months_and_an_index(tmp_path):
    build(tmp_path)

    series = json.loads((tmp_path / "data" / "library" / "fastapi.json").read_text())
    index = json.loads((tmp_path / "data" / "library" / "index.json").read_text())

    assert series == {
        "project": "fastapi",
        "months": ["2024-02-01", "2024-03-01"],
        "downloads": [40, None],
        "share": [4.0, None],
    }
    assert index == [{"project": "fastapi", "slug": "fastapi"}]


def test_a_hostile_project_name_stays_inside_the_data_directory(tmp_path):
    build(tmp_path, pages=[view("../../evil")], data=browse(row("../../evil")))

    assert not (tmp_path.parent / "evil.json").exists()
    assert len(list((tmp_path / "data" / "library").glob("*.json"))) == 2


def test_the_home_page_adds_movers_and_the_domains(tmp_path):
    build(tmp_path)

    html = read(tmp_path, "")

    assert 'href="/en/library/fastapi/"' in html and "+1.25" in html
    assert "<polyline" in html
    assert 'href="/en/domain/development/"' in html


def test_the_library_page_places_itself_in_the_catalog(tmp_path):
    build(tmp_path)

    html = read(tmp_path, "library/fastapi")

    assert 'href="/en/domain/development/"' in html and 'href="/en/category/web/"' in html
    assert 'href="/en/library/?tag=async"' in html
    assert 'class="library domain-development"' in html
    assert 'href="https://github.com/fastapi/fastapi" rel="noopener noreferrer"' in html


def test_renames_link_both_ways_and_are_never_added_up(tmp_path):
    build(tmp_path, pages=[view(renamed_from="old", renamed_to="new")])

    html = read(tmp_path, "library/fastapi")

    assert 'href="/en/library/old/"' in html and 'href="/en/library/new/"' in html


def share_payload(html):
    return json.loads(re.search(r'id="chart-share-data"[^>]*>(.*?)</script>', html, re.S)[1])


def test_the_library_page_charts_closed_months_of_share(tmp_path):
    build(tmp_path)

    payload = share_payload(read(tmp_path, "library/fastapi"))

    assert payload["option"]["series"][0]["data"] == [["2024-02-01", 4.0], ["2024-03-01", None]]
    assert payload["format"] == "percent"


def stars():
    points = (
        StarPoint(week=date(2024, 1, 7), stars=10),
        StarPoint(week=date(2024, 1, 14), stars=15),
    )
    return StarsView(repo="fastapi/fastapi", total=15, points=points, shared_with=())


def test_stars_have_their_own_chart_and_method_note(tmp_path):
    build(tmp_path, pages=[view(stars=stars())])

    html = read(tmp_path, "library/fastapi")
    payload = json.loads(re.search(r'id="chart-stars-data"[^>]*>(.*?)</script>', html, re.S)[1])

    assert payload["option"]["series"][0]["data"][-1] == ["2024-01-14", 15]
    assert "net" in html
    assert "15" in html


def test_a_shared_repo_is_stated(tmp_path):
    shared = stars().model_copy(update={"shared_with": ("fastapi-cli",)})
    build(tmp_path, pages=[view(stars=shared)])

    assert 'href="/en/library/fastapi-cli/"' in read(tmp_path, "library/fastapi")


@pytest.mark.parametrize(
    ("changes", "english"),
    [
        ({"repo": None}, "No GitHub repository"),
        ({"repo": "a/b", "stars": None}, "No star data yet"),
    ],
)
def test_missing_stars_are_explained(tmp_path, changes, english):
    build(tmp_path, pages=[view(**changes)])

    assert english in read(tmp_path, "library/fastapi")


class Inline(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "style" or "style" in attributes:
            self.found.append(tag)
        if (
            tag == "script"
            and "src" not in attributes
            and attributes.get("type") != "application/json"
        ):
            self.found.append(tag)
        if any(name.startswith("on") for name in attributes):
            self.found.append(tag)


def test_no_page_has_inline_script_or_style(tmp_path):
    build(tmp_path, pages=[view(stars=stars())])

    pages = list(tmp_path.rglob("index.html"))

    assert len(pages) >= 14
    for page in pages:
        parser = Inline()
        parser.feed(page.read_text())
        assert parser.found == [], page


def test_external_names_are_escaped_in_listings(tmp_path):
    build(tmp_path, data=browse(row("<script>alert(1)</script>")))

    html = read(tmp_path, "library")

    assert "<script>alert" not in html and "&lt;script&gt;alert" in html
