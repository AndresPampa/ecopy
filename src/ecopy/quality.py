"""Calendario de calidad de la fuente: huecos y días degradados, conocidos y globales.

No es un flag en el store: un hueco no tiene filas donde marcarlo y los períodos valen para todos
los paquetes. Regla de los degradados: día por debajo de 0,5 de la mediana de los 4 mismos días
de semana previos (`docs/spikes/s7-clickpy-revisiones-y-umbrales.md`).
"""

from __future__ import annotations

from datetime import date, timedelta
from enum import StrEnum

from ecopy.models import Coverage

SOURCE_START = date(2016, 1, 22)
"""Primer día con datos en ClickPy (spike S1)."""

_GAPS = (
    (date(2016, 3, 6), date(2016, 5, 21)),  # 03-06 tiene 5 descargas en total; el resto, nada
    (date(2019, 4, 26), date(2019, 4, 27)),
)
_DEGRADED = (
    (date(2016, 12, 8), date(2016, 12, 8)),
    (date(2017, 5, 11), date(2017, 5, 11)),
    (date(2018, 4, 17), date(2018, 4, 17)),
    (date(2018, 7, 11), date(2018, 7, 26)),
    (date(2019, 4, 13), date(2019, 4, 13)),
    (date(2019, 4, 25), date(2019, 4, 25)),
    (date(2019, 4, 28), date(2019, 4, 28)),
)


class DayQuality(StrEnum):
    OK = "ok"
    GAP = "gap"
    DEGRADED = "degraded"


def _within(day: date, windows: tuple[tuple[date, date], ...]) -> bool:
    return any(first <= day <= last for first, last in windows)


def day_quality(day: date) -> DayQuality:
    if day < SOURCE_START or _within(day, _GAPS):
        return DayQuality.GAP
    return DayQuality.DEGRADED if _within(day, _DEGRADED) else DayQuality.OK


def period_coverage(first: date, last: date) -> Coverage:
    """Cuántos días del período (ambos extremos incluidos) tiene cada calidad."""
    qualities = [
        day_quality(first + timedelta(days=offset)) for offset in range((last - first).days + 1)
    ]
    return Coverage(
        expected=len(qualities),
        gap=qualities.count(DayQuality.GAP),
        degraded=qualities.count(DayQuality.DEGRADED),
    )
