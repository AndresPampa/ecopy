"""Render de las páginas: Jinja2 con autoescape, sin contenido inline."""

from __future__ import annotations

import hashlib
import re
import shutil
from collections.abc import Sequence
from pathlib import Path

from jinja2 import Environment, PackageLoader, StrictUndefined
from pydantic import BaseModel

from ecopy.models import LibraryView, SiteStatus

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
) -> None:
    """Escribe en `out` una página por librería e idioma, los estáticos y `_headers`."""
    out = Path(out)
    status = status or SiteStatus()
    _copy_static(out)
    (out / "_headers").write_text(HEADERS, encoding="utf-8")
    env = Environment(
        loader=PackageLoader("ecopy.site", "templates"),
        autoescape=True,
        undefined=StrictUndefined,
    )
    env.filters["number"] = _number
    template = env.get_template("library.html")
    for view in pages:
        slug = _slug(view.project)
        for lang in langs:
            other = next(code for code in LANGS if code != lang)
            path = out / lang / "library" / slug / "index.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                template.render(
                    view=view,
                    status=status,
                    lang=lang,
                    other=other,
                    slug=slug,
                    t=TEXTS[lang],
                    echarts=ECHARTS_FILE,
                    chart=_chart(view, TEXTS[lang]),
                ),
                encoding="utf-8",
            )
