"""Métricas: funciones puras sobre las series, sin E/S."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from datetime import date, timedelta

from ecopy.models import DailySeries, LibraryView, MonthPoint, YearTotal

# La fuente arranca el 2016-01-22 y le faltan 77 días de ese año (spike S1).
PARTIAL_YEARS = frozenset({2016})


def _next_month(month: date) -> date:
    return date(month.year + (month.month == 12), month.month % 12 + 1, 1)


def _months(first: date, last: date) -> Iterator[date]:
    month = first
    while month <= last:
        yield month
        month = _next_month(month)


def _in_progress(month: date, as_of: date) -> bool:
    """El mes de `as_of` está en curso salvo que `as_of` sea su último día."""
    return month == as_of.replace(day=1) and _next_month(month) != as_of + timedelta(days=1)


def _yearly(observed: DailySeries, as_of: date) -> tuple[YearTotal, ...]:
    totals: dict[int, int] = defaultdict(int)
    for day, downloads in observed.items():
        totals[day.year] += downloads
    year_closed = (as_of.month, as_of.day) == (12, 31)
    return tuple(
        YearTotal(
            year=year,
            downloads=downloads,
            partial=year in PARTIAL_YEARS,
            ytd=year == as_of.year and not year_closed,
        )
        for year, downloads in sorted(totals.items())
    )


def library_view(project: str, series: DailySeries, *, as_of: date) -> LibraryView:
    totals: dict[date, int] = defaultdict(int)
    observed = {day: n for day, n in series.items() if day <= as_of}
    if not observed:
        raise ValueError(f"{project}: sin datos hasta {as_of}")
    for day, downloads in observed.items():
        totals[day.replace(day=1)] += downloads
    monthly = tuple(
        MonthPoint(month=m, downloads=totals.get(m), partial=_in_progress(m, as_of))
        for m in _months(min(totals), as_of.replace(day=1))
    )
    closed = [m for m in monthly if not m.partial and m.downloads is not None]
    return LibraryView(
        project=project,
        first_date=min(observed),
        last_closed_month=closed[-1] if closed else None,
        monthly=monthly,
        yearly=_yearly(observed, as_of),
    )
