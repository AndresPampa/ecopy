"""Render estático de la ficha: HTML generado a partir de modelos de vista fijos."""

import hashlib
import json
import os
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import pytest

from ecopy.models import (
    CategoryShare,
    Coverage,
    DomainShare,
    LibraryView,
    MonthPoint,
    Mover,
    Newcomer,
    PythonVersionShare,
    SiteStatus,
    TimelineEvent,
    VolumeView,
    YearTotal,
    YearView,
)
from ecopy.site import render as site_render
from ecopy.site import render_site

SNAPSHOTS = Path(__file__).parent / "snapshots"


FULL = Coverage(expected=31, gap=0, degraded=0)


def view(project: str = "fastapi") -> LibraryView:
    months = (
        MonthPoint(month=date(2024, 1, 1), downloads=35_561_750, status="complete", coverage=FULL),
        MonthPoint(month=date(2024, 2, 1), downloads=None, status="complete", coverage=FULL),
        MonthPoint(month=date(2024, 3, 1), downloads=40_000_000, status="complete", coverage=FULL),
        MonthPoint(month=date(2024, 4, 1), downloads=1_000, status="in_progress", coverage=FULL),
    )
    return LibraryView(
        project=project,
        first_date=date(2024, 1, 1),
        last_closed_month=months[2],
        monthly=months,
        yearly=(
            YearTotal(
                year=2016,
                downloads=1_234,
                status="source_gap",
                coverage=Coverage(expected=366, gap=98, degraded=1),
            ),
            YearTotal(
                year=2018,
                downloads=2_000,
                status="package_start",
                coverage=Coverage(expected=24, gap=0, degraded=0),
            ),
            YearTotal(
                year=2019,
                downloads=3_000,
                status="degraded",
                coverage=Coverage(expected=365, gap=0, degraded=3),
            ),
            YearTotal(year=2023, downloads=4_000, status="complete", coverage=FULL),
            YearTotal(year=2024, downloads=75_562_750, status="in_progress", coverage=FULL),
        ),
    )


def page(out, lang: str = "en", project: str = "fastapi") -> str:
    return (out / lang / "library" / project / "index.html").read_text()


def test_each_library_gets_a_page_per_language_with_localized_figures(tmp_path):
    render_site([view()], tmp_path)

    english, spanish = page(tmp_path, "en"), page(tmp_path, "es")

    assert '<html lang="en">' in english and '<html lang="es">' in spanish
    assert "<h1>fastapi</h1>" in english
    assert "75,562,750" in english and "75.562.750" in spanish


def test_year_status_and_data_gaps_are_labelled_in_each_language(tmp_path):
    render_site([view()], tmp_path)

    english, spanish = page(tmp_path, "en"), page(tmp_path, "es")

    assert "Source gaps (268 of 366 days)" in english
    assert "Huecos de la fuente (268 de 366 días)" in spanish
    assert "Since first release" in english and "Desde el primer release" in spanish
    assert "Degraded days (3)" in english and "Días degradados (3)" in spanish
    assert "Year to date" in english and "Año en curso" in spanish
    assert "No data" in english and "Sin datos" in spanish


def test_pages_link_to_the_other_language(tmp_path):
    render_site([view()], tmp_path)

    assert 'href="/es/library/fastapi/"' in page(tmp_path, "en")
    assert 'href="/en/library/fastapi/"' in page(tmp_path, "es")


def test_external_project_name_is_escaped_and_cannot_leave_the_output(tmp_path):
    out = tmp_path / "site"

    render_site([view("../<script>alert(1)</script>")], out)

    written = [p for p in tmp_path.rglob("index.html")]
    assert len(written) == 2
    assert all(out in p.parents for p in written)
    html = written[0].read_text()
    assert "<script>alert(1)" not in html
    assert "&lt;script&gt;alert(1)" in html


class InlineContent(HTMLParser):
    """Junta lo que la CSP bloquearía: scripts y estilos en línea."""

    def __init__(self) -> None:
        super().__init__()
        self.found: list[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "style" or "style" in attributes:
            self.found.append(f"estilo en <{tag}>")
        is_data = attributes.get("type") == "application/json"
        if tag == "script" and "src" not in attributes and not is_data:
            self.found.append("script en línea")
        if any(name.startswith("on") for name in attributes):
            self.found.append(f"handler en <{tag}>")


def test_headers_file_declares_the_strict_csp(tmp_path):
    render_site([view()], tmp_path)

    headers = (tmp_path / "_headers").read_text()

    assert headers.startswith("/*\n")
    assert "default-src 'none'" in headers
    assert "script-src 'self'" in headers
    assert "style-src 'self'" in headers
    assert "frame-ancestors 'none'" in headers


@pytest.mark.parametrize("lang", ["en", "es"])
def test_pages_have_no_inline_script_or_style(tmp_path, lang):
    render_site([view()], tmp_path)
    parser = InlineContent()

    parser.feed(page(tmp_path, lang))

    assert parser.found == []


def test_echarts_and_its_license_are_served_from_the_site(tmp_path):
    render_site([view()], tmp_path)
    vendor = tmp_path / "static" / "vendor"

    library = (vendor / "echarts-6.1.0.common.min.js").read_bytes()

    assert hashlib.sha256(library).hexdigest() == (
        "61f13280aba3161f77fc801bf5f9c786f55f10432153a0683fc5cc0700b013d5"
    )
    assert (vendor / "ECHARTS-LICENSE.txt").exists()
    assert (vendor / "ECHARTS-NOTICE.txt").exists()
    assert '<script src="/static/vendor/echarts-6.1.0.common.min.js" defer>' in page(tmp_path)


def test_build_fails_if_the_bundled_echarts_does_not_match_its_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(site_render, "ECHARTS_SHA256", "0" * 64)

    with pytest.raises(site_render.AssetIntegrityError):
        render_site([view()], tmp_path)


def chart(html: str) -> dict:
    data = re.search(r'<script id="chart-data" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(data.group(1))


def test_the_line_stops_at_the_last_closed_month_and_keeps_gaps(tmp_path):
    render_site([view()], tmp_path)

    series = chart(page(tmp_path))["option"]["series"]

    assert len(series) == 1
    assert series[0]["data"] == [
        ["2024-01-01", 35_561_750],
        ["2024-02-01", None],
        ["2024-03-01", 40_000_000],
        ["2024-04-01", None],
    ]


def test_the_month_in_progress_is_a_band_with_its_partial_value(tmp_path):
    render_site([view()], tmp_path)

    payload = chart(page(tmp_path))

    band = payload["option"]["series"][0]["markArea"]["data"]
    assert band == [[{"xAxis": "2024-04-01"}, {"xAxis": "2024-05-01"}]]
    assert payload["option"]["xAxis"]["max"] == "2024-05-01"
    assert payload["inProgress"] == {"month": "2024-04-01", "downloads": 1_000}


def test_the_month_in_progress_is_explained_in_days(tmp_path):
    months = list(view().monthly)
    partial = Coverage(expected=8, gap=0, degraded=0)
    months[-1] = months[-1].model_copy(update={"coverage": partial})

    render_site([view().model_copy(update={"monthly": tuple(months)})], tmp_path)

    assert "2024-04 in progress: 1,000 downloads in 8 of 30 days" in page(tmp_path)
    assert "2024-04 en curso: 1.000 descargas en 8 de 30 días" in page(tmp_path, "es")


def test_a_series_without_a_month_in_progress_has_no_band(tmp_path):
    months = (MonthPoint(month=date(2024, 1, 1), downloads=5, status="complete", coverage=FULL),)
    closed_only = view().model_copy(update={"monthly": months, "last_closed_month": months[0]})

    render_site([closed_only], tmp_path)

    payload = chart(page(tmp_path))
    assert "markArea" not in payload["option"]["series"][0]
    assert payload["inProgress"] is None


def test_discontinuities_are_marked_on_the_chart(tmp_path):
    marked = view().model_copy(update={"discontinuities": (date(2024, 2, 15),)})

    render_site([marked], tmp_path)

    mark = chart(page(tmp_path))["option"]["series"][0]["markLine"]
    assert mark["data"] == [{"xAxis": "2024-02-15"}]
    assert mark["label"]["formatter"] == "discontinuity"
    assert mark["label"]["position"] == "end"


def test_chart_data_cannot_break_out_of_its_script_tag(tmp_path, monkeypatch):
    labels = dict(site_render.TEXTS["en"], no_data="</script><img src=x>")
    monkeypatch.setitem(site_render.TEXTS, "en", labels)

    render_site([view()], tmp_path)

    assert "</script><img" not in page(tmp_path)
    assert chart(page(tmp_path))["labels"]["noData"] == "</script><img src=x>"


@pytest.mark.parametrize("lang", ["en", "es"])
def test_page_matches_its_snapshot(tmp_path, lang):
    render_site([view()], tmp_path)
    snapshot = SNAPSHOTS / f"library-{lang}.html"

    if os.environ.get("UPDATE_SNAPSHOTS"):
        snapshot.write_text(page(tmp_path, lang))

    assert page(tmp_path, lang) == snapshot.read_text()


@pytest.mark.parametrize("name", ["..", "."])
def test_a_dot_project_name_stays_inside_the_library_directory(tmp_path, name):
    render_site([view(name)], tmp_path)

    assert not (tmp_path / "en" / "index.html").exists()
    assert not (tmp_path / "en" / "library" / "index.html").exists()
    assert len(list((tmp_path / "en" / "library").glob("*/index.html"))) == 1


def test_a_failed_update_is_announced_in_each_language_with_the_last_good_date(tmp_path):
    render_site([view()], tmp_path, status=SiteStatus(date(2024, 2, 1), failed=True))

    english, spanish = page(tmp_path, "en"), page(tmp_path, "es")

    assert "Update failed" in english and "2024-02-01" in english
    assert "Actualización fallida" in spanish and "2024-02-01" in spanish


def test_a_healthy_site_shows_its_last_update_and_no_notice(tmp_path):
    render_site([view()], tmp_path, status=SiteStatus(date(2024, 2, 1), failed=False))

    english = page(tmp_path)

    assert "Update failed" not in english
    assert "Last updated" in english and "2024-02-01" in english


def test_a_failure_without_a_good_date_still_warns(tmp_path):
    render_site([view()], tmp_path, status=SiteStatus(None, failed=True))

    assert "Update failed" in page(tmp_path)


LABELS = {
    "development": {"en": "Development", "es": "Desarrollo"},
    "web": {"en": "Web development", "es": "Desarrollo web"},
    "testing": {"en": "Testing", "es": "Testing"},
}


def year(number: int = 2024, status: str = "closed", **changes) -> YearView:
    base = {
        "year": number,
        "status": status,
        "methodology_version": 1,
        "period_start": date(number, 1, 1),
        "period_end": date(number, 12, 31),
        "previous_start": date(number - 1, 1, 1),
        "previous_end": date(number - 1, 12, 31),
        "coverage": Coverage(expected=366, gap=0, degraded=0),
        "volume": VolumeView(total=9_000, previous=6_000, growth=0.5, discontinuities=()),
        "catalog_share": 0.68,
        "domains": (
            DomainShare(
                slug="development",
                downloads=100,
                share=1.0,
                categories=(
                    CategoryShare(slug="web", downloads=75, share=0.75),
                    CategoryShare(slug="testing", downloads=25, share=0.25),
                ),
            ),
        ),
        "movers_up": (
            Mover(
                project="fastapi",
                category="web",
                share=0.2,
                share_change=1.25,
                rank=3,
                rank_change=2,
            ),
        ),
        "movers_down": (
            Mover(
                project="flask",
                category="web",
                share=0.1,
                share_change=-0.5,
                rank=8,
                rank_change=None,
            ),
        ),
        "newcomers": (Newcomer(project="uvicorn", category="web", rank=42),),
        "python_versions": (
            PythonVersionShare(version="3.12", downloads=75, share=0.75),
            PythonVersionShare(version="3.9", downloads=25, share=0.25),
        ),
        "python_unknown_share": 0.05,
        "python_other_share": 0.001,
        "timeline": (TimelineEvent(date=date(2024, 10, 7), version="3.13", kind="release"),),
    }
    return YearView(**{**base, **changes})


def year_page(out, number: int = 2024, lang: str = "en") -> str:
    return (out / lang / "year" / str(number) / "index.html").read_text()


def render_years(out, *views) -> None:
    render_site([], out, years=views or (year(),), labels=LABELS)


def test_each_year_gets_a_page_per_language_with_localized_figures(tmp_path):
    render_years(tmp_path)

    english, spanish = year_page(tmp_path), year_page(tmp_path, lang="es")

    assert "<h1>2024</h1>" in english
    assert "9,000" in english and "9.000" in spanish
    assert "75.0%" in english and "75,0 %" in spanish
    assert "Web development" in english and "Desarrollo web" in spanish


def test_a_year_page_shows_movers_newcomers_versions_and_timeline(tmp_path):
    render_years(tmp_path)

    english = year_page(tmp_path)

    assert "fastapi" in english and "+1.25" in english and "+2" in english
    assert "flask" in english and "-0.50" in english
    assert "uvicorn" in english and "#42" in english
    assert "3.12" in english and "3.13" in english
    assert 'href="/en/library/fastapi/"' in english


def test_the_year_page_states_its_methodology_and_catalog_coverage(tmp_path):
    render_years(tmp_path)

    english, spanish = year_page(tmp_path), year_page(tmp_path, lang="es")

    assert "Methodology version 1" in english and "Versión metodológica 1" in spanish
    assert "68.0%" in english and "68,0 %" in spanish


def test_volume_always_carries_its_warning(tmp_path):
    render_years(tmp_path)

    assert "not a measure of real users" in year_page(tmp_path)
    assert "no mide usuarios reales" in year_page(tmp_path, lang="es")


def test_growth_is_shown_when_comparable(tmp_path):
    render_years(tmp_path)

    assert "+50.0%" in year_page(tmp_path)


def test_a_discontinuity_replaces_the_growth_with_its_explanation(tmp_path):
    volume = VolumeView(
        total=9_000,
        previous=6_000,
        growth=None,
        discontinuities=(date(2018, 7, 27),),
    )

    render_years(tmp_path, year(2018, volume=volume))

    english = year_page(tmp_path, 2018)
    assert "+50.0%" not in english
    assert "2018-07-27" in english
    assert "Growth is not shown" in english


def test_a_year_in_progress_says_what_it_compares(tmp_path):
    view = year(
        2026,
        status="ytd",
        period_end=date(2026, 11, 8),
        previous_start=date(2025, 1, 1),
        previous_end=date(2025, 11, 8),
    )

    render_years(tmp_path, view)

    english, spanish = year_page(tmp_path, 2026), year_page(tmp_path, 2026, "es")
    assert "Year to date" in english and "2025-11-08" in english
    assert "Año en curso" in spanish


def test_the_first_year_explains_why_it_has_no_movers(tmp_path):
    view = year(
        2017,
        previous_start=None,
        previous_end=None,
        volume=VolumeView(total=5, previous=None, growth=None, discontinuities=()),
        movers_up=(),
        movers_down=(),
        newcomers=(),
    )

    render_years(tmp_path, view)

    assert "no complete previous year" in year_page(tmp_path, 2017)


def test_year_pages_link_to_each_other_and_to_the_other_language(tmp_path):
    render_years(tmp_path, year(2023), year(2024))

    english = year_page(tmp_path, 2024)

    assert 'href="/en/year/2023/"' in english
    assert 'href="/es/year/2024/"' in english


def test_the_language_index_lists_the_years(tmp_path):
    render_years(tmp_path, year(2023), year(2024))

    index = (tmp_path / "en" / "index.html").read_text()

    assert 'href="/en/year/2024/"' in index and 'href="/en/year/2023/"' in index


def test_every_page_has_the_header_with_home_navigation_and_language(tmp_path):
    render_site([view()], tmp_path, years=(year(),), labels=LABELS)

    for html in (page(tmp_path), year_page(tmp_path), (tmp_path / "en" / "index.html").read_text()):
        assert '<header class="site">' in html
        assert 'class="mark" href="/en/"' in html
        assert 'hreflang="es"' in html


def test_every_page_credits_its_author_with_links_to_their_profiles_and_the_source(tmp_path):
    render_site([view()], tmp_path, years=(year(),), labels=LABELS)
    texts = (("en", "Made by", "Source code"), ("es", "Hecho por", "Código fuente"))
    profiles = (
        ("https://github.com/AndresPampa", "GitHub"),
        ("https://www.instagram.com/andrespampa/", "Instagram"),
    )

    for lang, made_by, code in texts:
        pages = (
            page(tmp_path, lang),
            year_page(tmp_path, lang=lang),
            (tmp_path / lang / "index.html").read_text(),
        )
        for html in pages:
            footer = html[html.index('<footer class="site">') :]
            assert f"{made_by} AndresPampa" in footer
            for url, name in profiles:
                assert f'<a href="{url}" rel="me noopener">{name}</a>' in footer
            assert (
                f'<a href="https://github.com/AndresPampa/ecopy" rel="noopener">{code}</a>'
                in footer
            )


def test_every_page_offers_the_theme_switch_named_in_each_language(tmp_path):
    render_site([view()], tmp_path, years=(year(),), labels=LABELS)
    texts = (
        ("en", "Switch to the dark theme", "Switch to the light theme"),
        ("es", "Cambiar al tema oscuro", "Cambiar al tema claro"),
    )

    for lang, to_dark, to_light in texts:
        pages = (
            page(tmp_path, lang),
            year_page(tmp_path, lang=lang),
            (tmp_path / lang / "index.html").read_text(),
        )
        for html in pages:
            header = html[html.index('<header class="site">') : html.index("</header>")]
            assert 'class="chip theme-toggle"' in header
            assert 'data-name-dark="Pythonista"' in header
            assert 'data-name-light="Pythoneer"' in header
            assert f'data-label-dark="{to_dark} (Pythonista)"' in header
            assert f'data-label-light="{to_light} (Pythoneer)"' in header


def test_the_theme_switch_stays_hidden_until_its_script_runs(tmp_path):
    render_site([view()], tmp_path)

    button = re.search(r"<button[^>]*theme-toggle[^>]*>", page(tmp_path)).group(0)

    assert " hidden" in button


def test_the_saved_theme_is_applied_by_a_blocking_script_from_the_site(tmp_path):
    render_site([view()], tmp_path)

    head = page(tmp_path)[: page(tmp_path).index("</head>")]

    assert '<script src="/static/theme.js"></script>' in head
    assert (tmp_path / "static" / "theme.js").exists()


def test_the_dark_palette_is_the_same_for_the_system_and_for_the_switch():
    css = (site_render.STATIC / "site.css").read_text()

    def tokens(selector: str) -> list[str]:
        block = css[css.index(selector + " {") :]
        return re.findall(r"--[\w-]+: [^;]+;", block[: block.index("}")])

    from_system = tokens(':root:not([data-theme="light"])')

    assert len(from_system) > 10
    assert from_system == tokens(':root[data-theme="dark"]')


def test_the_current_section_is_marked_in_the_navigation(tmp_path):
    render_site([view()], tmp_path, years=(year(),), labels=LABELS)

    assert 'href="/en/" aria-current="page">Years' in year_page(tmp_path)
    assert 'aria-current="page"' not in page(tmp_path)


def test_a_partial_build_has_no_links_to_pages_it_did_not_write(tmp_path):
    render_site([view()], tmp_path)

    assert 'href="/en/"' not in page(tmp_path)


def domains(*shares) -> tuple[DomainShare, ...]:
    return tuple(
        DomainShare(slug=slug, downloads=int(share * 100), share=share, categories=())
        for slug, share in shares
    )


def test_the_home_page_draws_one_linked_column_per_year_with_a_segment_per_domain(tmp_path):
    views = (
        year(2023, domains=domains(("development", 0.75), ("data-ai", 0.25))),
        year(2024, domains=domains(("development", 0.5), ("data-ai", 0.5))),
    )

    render_years(tmp_path, *views)

    index = (tmp_path / "en" / "index.html").read_text()
    wide = index[index.index('class="strata wide"') :]
    wide = wide[: wide.index("</svg>")]
    assert wide.count("<rect") == 4
    assert wide.count('class="d-data-ai') == 2
    assert 'href="/en/year/2023/"' in wide and 'href="/en/year/2024/"' in wide


def test_the_strata_stack_the_featured_domain_at_the_base_in_any_input_order(tmp_path):
    render_years(tmp_path, year(2024, domains=domains(("infrastructure", 0.5), ("data-ai", 0.5))))

    index = (tmp_path / "en" / "index.html").read_text()
    wide = index[index.index('class="strata wide"') :]
    positions = dict(
        re.findall(r'class="d-([a-z-]+)" x="[^"]*" y="([\d.]+)"', wide[: wide.index("</svg>")])
    )

    assert float(positions["data-ai"]) > float(positions["infrastructure"])


def test_the_home_page_states_the_domain_that_gained_the_most_share(tmp_path):
    views = (
        year(2023, domains=domains(("development", 0.75), ("data-ai", 0.25))),
        year(2024, domains=domains(("development", 0.5), ("data-ai", 0.5))),
    )
    labels = {**LABELS, "data-ai": {"en": "Data & AI", "es": "Datos e IA"}}

    render_site([], tmp_path, years=views, labels=labels)

    english = (tmp_path / "en" / "index.html").read_text()
    spanish = (tmp_path / "es" / "index.html").read_text()
    assert "Data &amp; AI went from 25.0% of catalog downloads in 2023 to 50.0% in 2024." in english
    assert (
        "Datos e IA pasó de 25,0 % de las descargas del catálogo en 2023 a 50,0 % en 2024."
        in spanish
    )


def test_the_home_page_states_no_finding_when_no_domain_gained_share(tmp_path):
    same = domains(("development", 1.0))

    render_years(tmp_path, year(2023, domains=same), year(2024, domains=same))

    assert 'class="lead"' not in (tmp_path / "en" / "index.html").read_text()


def test_a_year_in_progress_is_marked_as_partial_on_the_home_page(tmp_path):
    views = (
        year(
            2026,
            status="ytd",
            period_end=date(2026, 11, 8),
            previous_start=date(2025, 1, 1),
            previous_end=date(2025, 11, 8),
        ),
    )

    render_years(tmp_path, *views)

    assert 'class="d-development partial"' in (tmp_path / "en" / "index.html").read_text()


def test_no_index_is_written_without_years(tmp_path):
    render_site([view()], tmp_path)

    assert not (tmp_path / "en" / "index.html").exists()


def test_external_project_names_are_escaped_on_year_pages(tmp_path):
    evil = Mover(
        project="<script>alert(1)</script>",
        category="web",
        share=0.1,
        share_change=1.0,
        rank=1,
        rank_change=None,
    )

    render_years(tmp_path, year(movers_up=(evil,)))

    english = year_page(tmp_path)
    assert "<script>alert" not in english
    assert "&lt;script&gt;alert" in english


@pytest.mark.parametrize("lang", ["en", "es"])
def test_year_pages_have_no_inline_script_or_style(tmp_path, lang):
    render_years(tmp_path)

    html = year_page(tmp_path, lang=lang)

    assert " style=" not in html
    scripts = re.findall(r"<script([^>]*)>(.*?)</script>", html, flags=re.S)
    assert all(
        'type="application/json"' in attrs or (' src="' in attrs and not body)
        for attrs, body in scripts
    )


def charts(out, number: int = 2024) -> dict[str, dict]:
    html = year_page(out, number)
    found = re.findall(
        r'<script id="(chart-[a-z]+)-data" type="application/json">(.*?)</script>', html, re.S
    )
    return {name: json.loads(body) for name, body in found}


def test_year_charts_are_typed_data_with_a_container_each(tmp_path):
    render_years(tmp_path, year(2023), year(2024))

    found = charts(tmp_path)

    assert set(found) == {"chart-shares", "chart-python", "chart-volume"}
    for name in found:
        assert f'id="{name}"' in year_page(tmp_path)
    assert found["chart-shares"]["format"] == "percent"
    assert found["chart-volume"]["format"] == "compact"


def test_the_share_chart_ranks_categories_with_their_labels(tmp_path):
    render_years(tmp_path)

    option = charts(tmp_path)["chart-shares"]["option"]

    assert option["yAxis"]["data"] == ["Web development", "Testing"]
    assert option["series"][0]["data"] == [75.0, 25.0]


def test_the_share_chart_stops_at_twelve_categories(tmp_path):
    many = tuple(CategoryShare(slug=f"c{i}", downloads=20 - i, share=0.05) for i in range(20))
    domain = DomainShare(slug="development", downloads=100, share=1.0, categories=many)

    render_years(tmp_path, year(domains=(domain,)))

    assert len(charts(tmp_path)["chart-shares"]["option"]["yAxis"]["data"]) == 12


def test_the_python_chart_skips_versions_under_one_percent(tmp_path):
    versions = (
        PythonVersionShare(version="3.12", downloads=995, share=0.995),
        PythonVersionShare(version="3.1", downloads=5, share=0.005),
    )

    render_years(tmp_path, year(python_versions=versions))

    assert charts(tmp_path)["chart-python"]["option"]["yAxis"]["data"] == ["3.12"]


def test_the_volume_chart_covers_all_years_and_flags_special_ones(tmp_path):
    jump = VolumeView(total=5, previous=2, growth=None, discontinuities=(date(2018, 7, 27),))
    views = (
        year(2018, volume=jump),
        year(2019),
        year(
            2026,
            status="ytd",
            period_end=date(2026, 11, 8),
            previous_start=date(2025, 1, 1),
            previous_end=date(2025, 11, 8),
        ),
    )

    render_years(tmp_path, *views)

    option = charts(tmp_path, 2019)["chart-volume"]["option"]
    assert option["xAxis"]["data"] == ["2018*", "2019", "2026 YTD"]
    assert option["series"][0]["data"][-1]["itemStyle"] == {"opacity": 0.55}


def test_categories_are_visually_nested_under_their_domain(tmp_path):
    render_years(tmp_path)

    assert year_page(tmp_path).count('<tr class="nested">') == 2


def test_year_table_shows_the_leading_python_version_of_every_year(tmp_path):
    render_years(tmp_path, year(2023), year(2024))

    assert year_page(tmp_path).count("<td>3.12</td>") >= 2


@pytest.mark.parametrize("lang", ["en", "es"])
def test_year_page_matches_its_snapshot(tmp_path, lang):
    render_years(tmp_path, year(2023), year(2024))
    snapshot = SNAPSHOTS / f"year-{lang}.html"

    if os.environ.get("UPDATE_SNAPSHOTS"):
        snapshot.write_text(year_page(tmp_path, lang=lang))

    assert year_page(tmp_path, lang=lang) == snapshot.read_text()
