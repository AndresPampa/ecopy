"""Geometría de los SVG generados en Python. Las plantillas los escriben con autoescape."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from ecopy.models import ReleasesView, YearView

STRATA_ORDER = (
    "data-ai",
    "development",
    "multimedia-specialized",
    "utilities",
    "infrastructure",
)
"""De la base hacia arriba: el dominio que cuenta la historia va sobre la base."""

_GAP_BETWEEN_SEGMENTS = 2
_MIN_SEGMENT = 1
_LABEL_BAND = 26
_BOTTOM = 8


@dataclass(frozen=True)
class Segment:
    slug: str
    share: float
    y: float
    height: float


@dataclass(frozen=True)
class Column:
    year: int
    label: str
    x: float
    partial: bool
    segments: tuple[Segment, ...]


@dataclass(frozen=True)
class Strata:
    width: int
    height: int
    column: float
    font: int
    columns: tuple[Column, ...]


def _order(slug: str) -> tuple[int, str]:
    position = STRATA_ORDER.index(slug) if slug in STRATA_ORDER else len(STRATA_ORDER)
    return position, slug


def strata(
    years: Sequence[YearView], *, width: int, height: int, gap: int, font: int, short: bool = False
) -> Strata:
    """Una columna por año, con un segmento por dominio apilado desde la base."""
    column = (width - gap * (len(years) - 1)) / len(years)
    plot = height - _LABEL_BAND - _BOTTOM
    columns = []
    for index, view in enumerate(years):
        bottom = float(height - _BOTTOM)
        segments = []
        for domain in sorted(view.domains, key=lambda d: _order(d.slug)):
            size = plot * domain.share
            bottom -= size
            drawn = max(size - _GAP_BETWEEN_SEGMENTS, _MIN_SEGMENT)
            segments.append(
                Segment(domain.slug, domain.share, round(bottom + 1, 1), round(drawn, 1))
            )
        columns.append(
            Column(
                year=view.year,
                label=f"'{str(view.year)[2:]}" if short else str(view.year),
                x=round(index * (column + gap), 1),
                partial=view.status == "ytd",
                segments=tuple(segments),
            )
        )
    return Strata(width, height, round(column, 1), font, tuple(columns))


@dataclass(frozen=True)
class Spark:
    points: str
    last_x: float
    last_y: float


_SPARK_WIDTH = 120
_SPARK_HEIGHT = 28
_SPARK_PAD = 3


def sparkline(values: Sequence[float]) -> Spark | None:
    """Polilínea con escala propia: compara trayectorias, no magnitudes."""
    if len(values) < 2:
        return None
    low, span = min(values), (max(values) - min(values)) or 1.0
    plot_w = _SPARK_WIDTH - 2 * _SPARK_PAD
    plot_h = _SPARK_HEIGHT - 2 * _SPARK_PAD
    coordinates = [
        (
            round(_SPARK_PAD + i * plot_w / (len(values) - 1), 1),
            round(_SPARK_HEIGHT - _SPARK_PAD - (value - low) * plot_h / span, 1),
        )
        for i, value in enumerate(values)
    ]
    points = " ".join(f"{x},{y}" for x, y in coordinates)
    return Spark(points, *coordinates[-1])


@dataclass(frozen=True)
class LifeBar:
    version: str
    x: float
    width: float
    y: float
    supported: bool


@dataclass(frozen=True)
class Lifecycle:
    width: int
    height: int
    today_x: float
    bars: tuple[LifeBar, ...]
    ticks: tuple[tuple[int, float], ...]


_LIFE_LEFT = 56
_LIFE_RIGHT = 12
_LIFE_ROW = 22
_LIFE_TOP = 24
_LIFE_TODAY_CLEARANCE = 48


def lifecycle(view: ReleasesView, *, width: int = 1000) -> Lifecycle:
    """Una barra por versión con fin de soporte publicado, de lanzamiento a fin de soporte."""
    rows = [r for r in view.releases if r.end_of_life]
    if not rows:
        return Lifecycle(width, _LIFE_TOP, 0.0, (), ())
    start = min(r.released for r in rows).toordinal()
    end = max(max(r.end_of_life for r in rows), view.as_of).toordinal()
    scale = (width - _LIFE_LEFT - _LIFE_RIGHT) / (end - start)

    def place(day: date) -> float:
        return round(_LIFE_LEFT + (day.toordinal() - start) * scale, 1)

    bars = tuple(
        LifeBar(
            r.version,
            place(r.released),
            round(place(r.end_of_life) - place(r.released), 1),
            _LIFE_TOP + i * _LIFE_ROW,
            r.status == "supported",
        )
        for i, r in enumerate(rows)
    )
    first_year = date.fromordinal(start).year + 1
    last_year = date.fromordinal(end).year
    today = place(view.as_of)
    ticks = tuple(
        (y, place(date(y, 1, 1)))
        for y in range(first_year, last_year + 1, 2)
        if abs(place(date(y, 1, 1)) - today) > _LIFE_TODAY_CLEARANCE
    )
    return Lifecycle(width, _LIFE_TOP + len(rows) * _LIFE_ROW, today, bars, ticks)
