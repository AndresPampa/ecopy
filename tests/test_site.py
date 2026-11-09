"""Render estático de la ficha: HTML generado a partir de modelos de vista fijos."""

import hashlib
import json
import os
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import pytest

from ecopy.models import LibraryView, MonthPoint, YearTotal
from ecopy.site import render as site_render
from ecopy.site import render_site

SNAPSHOTS = Path(__file__).parent / "snapshots"


def view(project: str = "fastapi") -> LibraryView:
    months = (
        MonthPoint(month=date(2024, 1, 1), downloads=35_561_750, partial=False),
        MonthPoint(month=date(2024, 2, 1), downloads=None, partial=False),
        MonthPoint(month=date(2024, 3, 1), downloads=40_000_000, partial=False),
        MonthPoint(month=date(2024, 4, 1), downloads=1_000, partial=True),
    )
    return LibraryView(
        project=project,
        first_date=date(2024, 1, 1),
        last_closed_month=months[2],
        monthly=months,
        yearly=(
            YearTotal(year=2016, downloads=1_234, partial=True, ytd=False),
            YearTotal(year=2024, downloads=75_562_750, partial=False, ytd=True),
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

    assert "Partial data" in english and "Datos parciales" in spanish
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


def test_chart_keeps_gaps_and_draws_the_month_in_progress_apart(tmp_path):
    render_site([view()], tmp_path)

    payload = chart(page(tmp_path))
    closed, in_progress = payload["option"]["series"]

    assert closed["data"] == [
        ["2024-01-01", 35_561_750],
        ["2024-02-01", None],
        ["2024-03-01", 40_000_000],
        ["2024-04-01", None],
    ]
    assert in_progress["lineStyle"]["type"] == "dashed"
    assert in_progress["data"] == [["2024-03-01", 40_000_000], ["2024-04-01", 1_000]]
    assert payload["inProgressMonth"] == "2024-04-01"


def test_a_series_without_a_month_in_progress_has_a_single_line(tmp_path):
    months = (MonthPoint(month=date(2024, 1, 1), downloads=5, partial=False),)
    closed_only = view().model_copy(update={"monthly": months, "last_closed_month": months[0]})

    render_site([closed_only], tmp_path)

    payload = chart(page(tmp_path))
    assert len(payload["option"]["series"]) == 1
    assert payload["inProgressMonth"] is None


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
