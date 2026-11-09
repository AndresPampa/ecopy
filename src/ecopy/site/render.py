"""Render de las páginas: Jinja2 con autoescape, sin contenido inline."""

from __future__ import annotations

import hashlib
import re
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal

from jinja2 import Environment, PackageLoader, StrictUndefined
from pydantic import BaseModel

from ecopy.models import LibraryView, SiteStatus, YearView

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

TEXTS = {
    "en": {
        "switch_label": "Español",
        "first_data": "First day with data",
        "last_closed": "Last closed month",
        "yearly_title": "Downloads per year",
        "monthly_title": "Downloads per month",
        "year": "Year",
        "month": "Month",
        "downloads": "Downloads",
        "status": "Status",
        "package_start": "Since first release",
        "source_gap": "Source gaps ({with_data} of {expected} days)",
        "degraded": "Degraded days ({degraded})",
        "ytd": "Year to date",
        "in_progress": "In progress",
        "complete": "Complete",
        "no_data": "No data",
        "chart_alt": "Line chart of downloads per month. The table has the same data.",
        "in_progress_note": "The dashed segment is the month in progress.",
        "source": "Data: ClickPy, from PyPI download logs.",
        "last_updated": "Last updated",
        "update_failed": "Update failed: the latest ingest did not pass validation.",
        "update_failed_since": "Figures are from the last good update, on {date}.",
        "years_title": "The Python ecosystem, year by year",
        "compared_with": "Compared with the same number of days from {start} to {end}.",
        "methodology": "Methodology version {version}.",
        "volume_title": "Total downloads on PyPI",
        "volume_warning": (
            "This volume is inflated by CI and grows for reasons unrelated to popularity: it is "
            "not a measure of real users."
        ),
        "volume_alt": "Bar chart of total downloads per year. The table has the same data.",
        "volume_note": (
            "* Year with a change in data collection. A lighter bar is a year in progress."
        ),
        "against_previous": "against the previous period.",
        "growth_hidden": "Growth is not shown: the comparison crosses a change in data collection.",
        "discontinuity": "The volume has a discontinuity on",
        "shares_title": "Share by domain and category",
        "shares_alt": "Bar chart of the twelve largest categories. The table has all of them.",
        "catalog_share": (
            "Shares are over the ecopy catalog, which is {share} of all PyPI downloads this period."
        ),
        "category": "Category",
        "share": "Share",
        "package": "Package",
        "share_points": "Change (share points)",
        "position": "Position",
        "movers_title": "Movers",
        "movers_up": "Biggest gains",
        "movers_down": "Biggest losses",
        "movers_note": (
            "Packages most people never install on purpose (the Foundations category) are left "
            "out of this list."
        ),
        "no_previous": "Not available: 2017 has no complete previous year to compare with.",
        "newcomers_title": "New in the top 100",
        "top_position": "Position in PyPI",
        "no_newcomers": "No new packages this period.",
        "python_title": "Python versions",
        "python_alt": (
            "Bar chart of the Python versions with at least 1% of downloads. The table has all of"
            " them."
        ),
        "python_note": (
            "Closed months only. Without a version: {unknown}. Other values that are not CPython "
            "releases: {other}."
        ),
        "version": "Version",
        "leading_title": "Most used version per year",
        "timeline_title": "Python timeline",
        "event_release": "released",
        "event_end_of_life": "end of support",
        "no_events": "No releases or end of support this period.",
    },
    "es": {
        "switch_label": "English",
        "first_data": "Primer día con datos",
        "last_closed": "Último mes cerrado",
        "yearly_title": "Descargas por año",
        "monthly_title": "Descargas por mes",
        "year": "Año",
        "month": "Mes",
        "downloads": "Descargas",
        "status": "Estado",
        "package_start": "Desde el primer release",
        "source_gap": "Huecos de la fuente ({with_data} de {expected} días)",
        "degraded": "Días degradados ({degraded})",
        "ytd": "Año en curso",
        "in_progress": "En curso",
        "complete": "Completo",
        "no_data": "Sin datos",
        "chart_alt": "Gráfico de líneas de descargas por mes. La tabla tiene los mismos datos.",
        "in_progress_note": "El tramo punteado es el mes en curso.",
        "source": "Datos: ClickPy, a partir de los registros de descargas de PyPI.",
        "last_updated": "Última actualización",
        "update_failed": "Actualización fallida: la última ingesta no pasó la validación.",
        "update_failed_since": "Las cifras son las de la última actualización válida, del {date}.",
        "years_title": "El ecosistema Python, año por año",
        "compared_with": "Comparado con la misma cantidad de días, del {start} al {end}.",
        "methodology": "Versión metodológica {version}.",
        "volume_title": "Descargas totales en PyPI",
        "volume_warning": (
            "Este volumen está inflado por CI y crece por razones ajenas a la popularidad: no "
            "mide usuarios reales."
        ),
        "volume_alt": (
            "Gráfico de barras de descargas totales por año. La tabla tiene los mismos datos."
        ),
        "volume_note": (
            "* Año con un cambio en la recolección de datos. Una barra más clara es un año en "
            "curso."
        ),
        "against_previous": "contra el período anterior.",
        "growth_hidden": (
            "El crecimiento no se muestra: la comparación cruza un cambio en la recolección de "
            "datos."
        ),
        "discontinuity": "El volumen tiene una discontinuidad el",
        "shares_title": "Cuota por dominio y categoría",
        "shares_alt": (
            "Gráfico de barras de las doce categorías más grandes. La tabla las tiene todas."
        ),
        "catalog_share": (
            "Las cuotas son sobre el catálogo de ecopy, que representa {share} de las descargas "
            "de PyPI en este período."
        ),
        "category": "Categoría",
        "share": "Cuota",
        "package": "Paquete",
        "share_points": "Cambio (puntos de cuota)",
        "position": "Posición",
        "movers_title": "Movers",
        "movers_up": "Mayores subas",
        "movers_down": "Mayores bajas",
        "movers_note": (
            "Los paquetes que casi nadie instala a propósito (la categoría Infraestructura base) "
            "no entran en esta lista."
        ),
        "no_previous": (
            "No disponible: 2017 no tiene un año anterior completo con el cual comparar."
        ),
        "newcomers_title": "Nuevos en el top 100",
        "top_position": "Posición en PyPI",
        "no_newcomers": "Sin paquetes nuevos en este período.",
        "python_title": "Versiones de Python",
        "python_alt": (
            "Gráfico de barras de las versiones de Python con al menos 1 % de las descargas. La "
            "tabla las tiene todas."
        ),
        "python_note": (
            "Solo meses cerrados. Sin versión: {unknown}. Otros valores que no son versiones de "
            "CPython: {other}."
        ),
        "version": "Versión",
        "leading_title": "Versión más usada por año",
        "timeline_title": "Línea de tiempo de Python",
        "event_release": "lanzamiento",
        "event_end_of_life": "fin de soporte",
        "no_events": "Sin lanzamientos ni fin de soporte en este período.",
    },
}


class AssetIntegrityError(Exception):
    """Un archivo vendorizado no coincide con su hash fijado."""


class _LineOption(BaseModel):
    """Opción de ECharts. Los colores y formatos de número los agrega `library.js`."""

    grid: dict
    xAxis: dict
    yAxis: dict
    tooltip: dict
    series: list[dict]


class _ChartPayload(BaseModel):
    option: _LineOption
    inProgressMonth: str | None
    labels: dict[str, str]


YEAR_MS = 365 * 24 * 3600 * 1000


def _line(data: list, *, line_type: str) -> dict:
    return {
        "type": "line",
        "showSymbol": False,
        "connectNulls": False,
        "lineStyle": {"width": 2, "cap": "round", "join": "round", "type": line_type},
        "data": data,
    }


def _chart(view: LibraryView, texts: dict[str, str]) -> dict:
    """Línea mensual; el mes en curso va punteado para no leerse como una caída."""
    months = view.monthly
    closed = [
        [m.month.isoformat(), None if m.status == "in_progress" else m.downloads] for m in months
    ]
    series = [_line(closed, line_type="solid")]
    current = months[-1] if months and months[-1].status == "in_progress" else None
    if current and current.downloads is not None:
        previous = months[-2:-1]
        bridge = [[m.month.isoformat(), m.downloads] for m in previous if m.downloads is not None]
        data = [*bridge, [current.month.isoformat(), current.downloads]]
        series.append(_line(data, line_type="dashed"))
    payload = _ChartPayload(
        option=_LineOption(
            grid={"left": 8, "right": 24, "top": 16, "bottom": 8, "containLabel": True},
            xAxis={
                "type": "time",
                "minInterval": YEAR_MS,
                "axisLabel": {"formatter": "{yyyy}", "hideOverlap": True},
                "splitLine": {"show": False},
            },
            yAxis={"type": "value", "min": 0},
            tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "line"}},
            series=series,
        ),
        inProgressMonth=current.month.isoformat() if current else None,
        labels={"inProgress": texts["in_progress"], "noData": texts["no_data"]},
    )
    return payload.model_dump()


class _BarOption(BaseModel):
    """Barras de una sola serie. Los colores y formatos de número los agrega `charts.js`."""

    grid: dict
    xAxis: dict
    yAxis: dict
    tooltip: dict
    series: list[dict]


class _BarPayload(BaseModel):
    option: _BarOption
    format: Literal["percent", "compact"]


_MAX_CHART_CATEGORIES = 12
_MIN_CHART_VERSION_SHARE = 0.01
_GRID = {"left": 8, "right": 24, "top": 16, "bottom": 8, "containLabel": True}
_ITEM_TOOLTIP = {"trigger": "item", "confine": True}


def _horizontal_bars(names: list[str], values: list[float]) -> dict:
    """Mayor arriba; extremo redondeado de 4 px sobre la base."""
    series = {
        "type": "bar",
        "barMaxWidth": 20,
        "itemStyle": {"borderRadius": [0, 4, 4, 0]},
        "data": values,
    }
    option = _BarOption(
        grid=_GRID,
        xAxis={"type": "value", "min": 0, "axisLabel": {"hideOverlap": True}},
        yAxis={"type": "category", "inverse": True, "data": names},
        tooltip=_ITEM_TOOLTIP,
        series=[series],
    )
    return _BarPayload(option=option, format="percent").model_dump()


def _volume_chart(years: Sequence[YearView]) -> dict:
    """Una barra por año; la del año en curso, más clara: no es comparable con uno cerrado."""
    names, data = [], []
    for year in years:
        mark = "*" if year.volume.discontinuities else ""
        ytd = year.status == "ytd"
        names.append(f"{year.year}{' YTD' if ytd else ''}{mark}")
        point = {"value": year.volume.total}
        data.append({**point, "itemStyle": {"opacity": 0.55}} if ytd else point)
    series = {
        "type": "bar",
        "barMaxWidth": 32,
        "itemStyle": {"borderRadius": [4, 4, 0, 0]},
        "data": data,
    }
    option = _BarOption(
        grid=_GRID,
        xAxis={"type": "category", "data": names},
        yAxis={"type": "value", "min": 0},
        tooltip=_ITEM_TOOLTIP,
        series=[series],
    )
    return _BarPayload(option=option, format="compact").model_dump()


def _year_charts(
    view: YearView, years: Sequence[YearView], labels: Mapping, lang: str
) -> dict[str, dict]:
    categories = sorted(
        (c for domain in view.domains for c in domain.categories), key=lambda c: -c.share
    )[:_MAX_CHART_CATEGORIES]
    versions = [v for v in view.python_versions if v.share >= _MIN_CHART_VERSION_SHARE]
    return {
        "shares": _horizontal_bars(
            [_label(c.slug, labels, lang) for c in categories],
            [round(100 * c.share, 2) for c in categories],
        ),
        "python": _horizontal_bars(
            [v.version for v in versions], [round(100 * v.share, 2) for v in versions]
        ),
        "volume": _volume_chart(years),
    }


def _label(slug: str, labels: Mapping, lang: str) -> str:
    return labels.get(slug, {}).get(lang) or slug


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


def render_site(
    pages: Sequence[LibraryView],
    out: Path,
    *,
    langs: Sequence[str] = LANGS,
    status: SiteStatus | None = None,
    years: Sequence[YearView] = (),
    labels: Mapping[str, Mapping[str, str]] | None = None,
) -> None:
    """Escribe en `out` fichas y años por idioma, los estáticos y `_headers`."""
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
        label=lambda slug, lang: _label(slug, labels, lang),
    )

    def write(path: Path, template: str, **context) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        html = env.get_template(template).render(echarts=ECHARTS_FILE, status=status, **context)
        path.write_text(html, encoding="utf-8")

    for lang in langs:
        other = next(code for code in LANGS if code != lang)
        common = {"lang": lang, "other": other, "t": TEXTS[lang]}
        for view in pages:
            slug = _slug(view.project)
            write(
                out / lang / "library" / slug / "index.html",
                "library.html",
                view=view,
                slug=slug,
                chart=_chart(view, TEXTS[lang]),
                **common,
            )
        for view in years:
            write(
                out / lang / "year" / str(view.year) / "index.html",
                "year.html",
                view=view,
                years=years,
                charts=_year_charts(view, years, labels, lang),
                **common,
            )
        if years:
            write(out / lang / "index.html", "index.html", years=years, **common)
