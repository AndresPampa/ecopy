"""Render de las páginas: Jinja2 con autoescape, sin contenido inline."""

from __future__ import annotations

import calendar
import hashlib
import json
import re
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path

from jinja2 import Environment, PackageLoader, StrictUndefined

from ecopy.models import BrowseView, LibraryView, SiteStatus, YearView
from ecopy.site import svg
from ecopy.site.charts import _chart, _year_charts, share_chart, stars_chart, year_share_chart
from ecopy.site.i18n import TEXTS, label

LANGS = ("en", "es")

ECHARTS_FILE = "echarts-6.1.0.common.min.js"
ECHARTS_SHA256 = "61f13280aba3161f77fc801bf5f9c786f55f10432153a0683fc5cc0700b013d5"

STATIC = Path(__file__).parent / "static"

CSP = "; ".join(
    [
        "default-src 'none'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "base-uri 'none'",
        "form-action 'none'",
        "frame-ancestors 'none'",
    ]
)

HEADERS = f"""/*
  Content-Security-Policy: {CSP}
  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer
"""


class AssetIntegrityError(Exception):
    """Un archivo vendorizado no coincide con su hash fijado."""


def _percent(value: float, lang: str) -> str:
    text = f"{100 * value:.1f}"
    return f"{text.replace('.', ',')} %" if lang == "es" else f"{text}%"


def _points(value: float, lang: str) -> str:
    text = f"{value:+.2f}"
    return text.replace(".", ",") if lang == "es" else text


def _growth(value: float, lang: str) -> str:
    text = f"{100 * value:+.1f}"
    return f"{text.replace('.', ',')} %" if lang == "es" else f"{text}%"


def _number(value: int, lang: str) -> str:
    text = f"{value:,}"
    return text.replace(",", ".") if lang == "es" else text


def _slug(project: str) -> str:
    """Nombre de directorio seguro: un nombre externo nunca sale del directorio de salida."""
    return re.sub(r"[^A-Za-z0-9._-]", "-", project).lstrip(".") or "-"


def _copy_static(out: Path) -> None:
    library = (STATIC / "vendor" / ECHARTS_FILE).read_bytes()
    if hashlib.sha256(library).hexdigest() != ECHARTS_SHA256:
        raise AssetIntegrityError(f"{ECHARTS_FILE} no coincide con su SHA-256 fijado")
    shutil.copytree(STATIC, out / "static", dirs_exist_ok=True)


def _in_progress_note(view: LibraryView, texts: Mapping[str, str], lang: str) -> str | None:
    current = view.monthly[-1] if view.monthly else None
    if current is None or current.status != "in_progress" or current.downloads is None:
        return None
    return texts["in_progress_note"].format(
        month=current.month.strftime("%Y-%m"),
        downloads=_number(current.downloads, lang),
        days=current.coverage.expected,
        total=calendar.monthrange(current.month.year, current.month.month)[1],
    )


def _finding(
    years: Sequence[YearView], labels: Mapping, texts: Mapping[str, str], lang: str
) -> str | None:
    """El dominio que más cuota ganó entre el primer año y el último, si alguno ganó."""
    if len(years) < 2:
        return None
    first = {d.slug: d.share for d in years[0].domains}
    last = {d.slug: d.share for d in years[-1].domains}
    gains = sorted(
        ((last[s] - first[s], s) for s in first if s in last), key=lambda g: (-g[0], g[1])
    )
    if not gains or gains[0][0] <= 0:
        return None
    slug = gains[0][1]
    return texts["finding"].format(
        domain=label(slug, labels, lang),
        first=_percent(first[slug], lang),
        last=_percent(last[slug], lang),
        y0=years[0].year,
        y1=years[-1].year,
    )


def _legend(years: Sequence[YearView]) -> list[dict]:
    """De arriba hacia abajo, en el mismo orden visual que las columnas."""
    first = {d.slug: d.share for d in years[0].domains}
    domains = sorted(years[-1].domains, key=lambda d: svg._order(d.slug), reverse=True)
    return [{"slug": d.slug, "share": d.share, "first": first.get(d.slug)} for d in domains]


_HOME_MOVERS = 5


def _write_compare_data(pages: Sequence[LibraryView], out: Path) -> None:
    """Un JSON por librería con sus meses cerrados y un índice de nombres."""
    directory = out / "data" / "library"
    directory.mkdir(parents=True, exist_ok=True)
    index = []
    for view in sorted(pages, key=lambda v: v.project):
        slug = _slug(view.project)
        closed = [m for m in view.monthly if m.status != "in_progress"]
        series = {
            "project": view.project,
            "months": [m.month.isoformat() for m in closed],
            "downloads": [m.downloads for m in closed],
            "share": [None if m.share is None else round(100 * m.share, 4) for m in closed],
        }
        (directory / f"{slug}.json").write_text(
            json.dumps(series, separators=(",", ":")), encoding="utf-8"
        )
        index.append({"project": view.project, "slug": slug})
    (directory / "index.json").write_text(
        json.dumps(index, separators=(",", ":")), encoding="utf-8"
    )


def _write_browse(write, browse: BrowseView, common: dict) -> None:
    write("library/", "catalog.html", "libraries", browse=browse, **common)
    write("compare/", "compare.html", "compare", **common)
    write(
        "python/",
        "python.html",
        "python",
        releases=browse.releases,
        lifecycle=svg.lifecycle(browse.releases),
        **common,
    )
    for domain in browse.domains:
        rows = sorted(
            (r for c in domain.categories for r in c.rows),
            key=lambda r: (-(r.downloads or 0), r.project),
        )
        write(
            f"domain/{domain.slug}/",
            "domain.html",
            "libraries",
            domain=domain,
            top=rows[:_DOMAIN_TOP],
            chart=year_share_chart(domain.shares),
            **common,
        )
        for category in domain.categories:
            write(
                f"category/{category.slug}/",
                "category.html",
                "libraries",
                category=category,
                chart=year_share_chart(category.shares),
                **common,
            )


_DOMAIN_TOP = 20


def render_site(
    pages: Sequence[LibraryView],
    out: Path,
    *,
    langs: Sequence[str] = LANGS,
    status: SiteStatus | None = None,
    years: Sequence[YearView] = (),
    labels: Mapping[str, Mapping[str, str]] | None = None,
    browse: BrowseView | None = None,
) -> None:
    """Escribe en `out` las páginas por idioma, los datos del comparador, estáticos y `_headers`."""
    out = Path(out)
    status = status or SiteStatus()
    labels = labels or {}
    _copy_static(out)
    (out / "_headers").write_text(HEADERS, encoding="utf-8")
    env = Environment(
        loader=PackageLoader("ecopy.site", "templates"),
        autoescape=True,
        undefined=StrictUndefined,
    )
    env.filters.update(
        number=_number,
        percent=_percent,
        points=_points,
        growth=_growth,
        slug=_slug,
        label=lambda slug, lang: label(slug, labels, lang),
        spark=svg.sparkline,
    )
    if browse is not None:
        _write_compare_data(pages, out)
    trends = {row.project: row.trend for row in browse.rows} if browse else {}

    def write(relative: str, template: str, section: str, **context) -> None:
        lang = context["lang"]
        path = out / lang / relative / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        html = env.get_template(template).render(
            echarts=ECHARTS_FILE, status=status, path=relative, section=section, **context
        )
        path.write_text(html, encoding="utf-8")

    for lang in langs:
        other = next(code for code in LANGS if code != lang)
        texts = TEXTS[lang]
        nav = [("years", "", texts["nav_years"])] if years else []
        if browse is not None:
            nav += [
                ("libraries", "library/", texts["nav_libraries"]),
                ("compare", "compare/", texts["nav_compare"]),
                ("python", "python/", texts["nav_python"]),
            ]
        common = {"lang": lang, "other": other, "t": texts, "nav": nav}
        for view in pages:
            slug = _slug(view.project)
            write(
                f"library/{slug}/",
                "library.html",
                "libraries",
                view=view,
                slug=slug,
                chart=_chart(view, texts),
                note=_in_progress_note(view, texts, lang),
                share=share_chart(view, texts),
                stars=stars_chart(view.stars, texts) if view.stars else None,
                **common,
            )
        for view in years:
            write(
                f"year/{view.year}/",
                "year.html",
                "years",
                view=view,
                years=years,
                charts=_year_charts(view, years, labels, lang),
                **common,
            )
        if years:
            write(
                "",
                "index.html",
                "years",
                years=years,
                finding=_finding(years, labels, texts, lang),
                wide=svg.strata(years, width=1000, height=470, gap=16, font=18),
                narrow=svg.strata(years, width=360, height=320, gap=8, font=12, short=True),
                legend=_legend(years),
                browse=browse,
                movers=years[-1].movers_up[:_HOME_MOVERS],
                trends=trends,
                **common,
            )
        if browse is not None:
            _write_browse(write, browse, common)
