"""Opciones de ECharts, validadas con Pydantic y serializadas en cada página."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Literal

from pydantic import BaseModel

from ecopy.models import LibraryView, StarsView, YearShare, YearView
from ecopy.site.i18n import label


class _LineOption(BaseModel):
    """Opción de ECharts. Los colores y formatos de número los agrega `library.js`."""

    grid: dict
    xAxis: dict
    yAxis: dict
    tooltip: dict
    series: list[dict]


class _ChartPayload(BaseModel):
    option: _LineOption
    inProgress: dict | None
    labels: dict[str, str]
    format: Literal["full", "percent", "compact"]


YEAR_MS = 365 * 24 * 3600 * 1000


def _next_month(month: date) -> date:
    return date(month.year + (month.month == 12), month.month % 12 + 1, 1)


def _line(data: list) -> dict:
    return {
        "type": "line",
        "showSymbol": False,
        "connectNulls": False,
        "lineStyle": {"width": 2, "cap": "round", "join": "round"},
        "data": data,
    }


def _time_option(series: list[dict], *, end: date | None = None, top: int = 16) -> _LineOption:
    axis = {
        "type": "time",
        "minInterval": YEAR_MS,
        "axisLabel": {"formatter": "{yyyy}", "hideOverlap": True},
        "splitLine": {"show": False},
    }
    return _LineOption(
        grid={"left": 8, "right": 24, "top": top, "bottom": 8, "containLabel": True},
        xAxis={**axis, "max": end.isoformat()} if end else axis,
        yAxis={"type": "value", "min": 0},
        tooltip={"trigger": "axis", "confine": True, "axisPointer": {"type": "line"}},
        series=series,
    )


def _chart(view: LibraryView, texts: dict[str, str]) -> dict:
    """Línea mensual hasta el último mes cerrado; el mes en curso es una franja, no un punto."""
    months = view.monthly
    data = [
        [m.month.isoformat(), None if m.status == "in_progress" else m.downloads] for m in months
    ]
    series = _line(data)
    current = months[-1] if months and months[-1].status == "in_progress" else None
    end = _next_month(current.month) if current else None
    if current:
        band = [{"xAxis": current.month.isoformat()}, {"xAxis": end.isoformat()}]
        series["markArea"] = {"silent": True, "data": [band]}
    if view.discontinuities:
        series["markLine"] = {
            "silent": True,
            "symbol": "none",
            "label": {"formatter": texts["discontinuity_mark"], "position": "end"},
            "data": [{"xAxis": day.isoformat()} for day in view.discontinuities],
        }
    payload = _ChartPayload(
        option=_time_option([series], end=end, top=32 if view.discontinuities else 16),
        inProgress=(
            {"month": current.month.isoformat(), "downloads": current.downloads}
            if current
            else None
        ),
        labels={"inProgress": texts["in_progress"], "noData": texts["no_data"]},
        format="full",
    )
    return payload.model_dump()


def _line_payload(data: list, texts: dict[str, str], fmt: str) -> dict:
    payload = _ChartPayload(
        option=_time_option([_line(data)]),
        inProgress=None,
        labels={"inProgress": texts["in_progress"], "noData": texts["no_data"]},
        format=fmt,
    )
    return payload.model_dump()


def share_chart(view: LibraryView, texts: dict[str, str]) -> dict:
    """Cuota mensual de PyPI, en meses cerrados."""
    data = [
        [m.month.isoformat(), None if m.share is None else round(100 * m.share, 4)]
        for m in view.monthly
        if m.status != "in_progress"
    ]
    return _line_payload(data, texts, "percent")


def stars_chart(stars: StarsView, texts: dict[str, str]) -> dict:
    return _line_payload([[p.week.isoformat(), p.stars] for p in stars.points], texts, "full")


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


def year_share_chart(shares: Sequence[YearShare]) -> dict:
    """Una barra por año; la del año en curso, más tenue."""
    names, data = [], []
    for share in shares:
        ytd = share.status == "ytd"
        names.append(f"{share.year}{' YTD' if ytd else ''}")
        point = {"value": round(100 * share.share, 2)}
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
    return _BarPayload(option=option, format="percent").model_dump()


def _year_charts(
    view: YearView, years: Sequence[YearView], labels: Mapping, lang: str
) -> dict[str, dict]:
    categories = sorted(
        (c for domain in view.domains for c in domain.categories), key=lambda c: -c.share
    )[:_MAX_CHART_CATEGORIES]
    versions = [v for v in view.python_versions if v.share >= _MIN_CHART_VERSION_SHARE]
    return {
        "shares": _horizontal_bars(
            [label(c.slug, labels, lang) for c in categories],
            [round(100 * c.share, 2) for c in categories],
        ),
        "python": _horizontal_bars(
            [v.version for v in versions], [round(100 * v.share, 2) for v in versions]
        ),
        "volume": _volume_chart(years),
    }
