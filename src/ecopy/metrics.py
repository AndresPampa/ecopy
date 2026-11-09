"""Métricas: funciones puras sobre las series, sin E/S."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator, Sequence
from datetime import date, timedelta

from ecopy.models import (
    Coverage,
    DailySeries,
    LibraryView,
    MonthPoint,
    PeriodStatus,
    RunReport,
    SiteStatus,
    YearTotal,
)
from ecopy.quality import SOURCE_START, period_coverage


def _next_month(month: date) -> date:
    return date(month.year + (month.month == 12), month.month % 12 + 1, 1)


def _months(first: date, last: date) -> Iterator[date]:
    month = first
    while month <= last:
        yield month
        month = _next_month(month)


def _period(
    start: date, end: date, *, first_date: date, as_of: date
) -> tuple[PeriodStatus, Coverage]:
    """Estado y cobertura del período [start, end] para un paquete con esa primera fecha."""
    # Antes del inicio de la fuente no se sabe si el paquete existía: se cuenta como hueco.
    counted_from = max(start, first_date) if first_date > SOURCE_START else start
    coverage = period_coverage(counted_from, min(end, as_of))
    if as_of < end:
        return "in_progress", coverage
    if start < first_date <= end and first_date > SOURCE_START:
        return "package_start", coverage
    if coverage.gap:
        return "source_gap", coverage
    return ("degraded" if coverage.degraded else "complete"), coverage


def _monthly(totals: dict[date, int], first_date: date, as_of: date) -> tuple[MonthPoint, ...]:
    points = []
    for month in _months(first_date.replace(day=1), as_of.replace(day=1)):
        end = _next_month(month) - timedelta(days=1)
        status, coverage = _period(month, end, first_date=first_date, as_of=as_of)
        points.append(
            MonthPoint(month=month, downloads=totals.get(month), status=status, coverage=coverage)
        )
    return tuple(points)


def _yearly(observed: DailySeries, first_date: date, as_of: date) -> tuple[YearTotal, ...]:
    totals: dict[int, int] = defaultdict(int)
    for day, downloads in observed.items():
        totals[day.year] += downloads
    years = []
    for year, downloads in sorted(totals.items()):
        status, coverage = _period(
            date(year, 1, 1), date(year, 12, 31), first_date=first_date, as_of=as_of
        )
        years.append(YearTotal(year=year, downloads=downloads, status=status, coverage=coverage))
    return tuple(years)


def library_view(project: str, series: DailySeries, *, as_of: date) -> LibraryView:
    totals: dict[date, int] = defaultdict(int)
    observed = {day: n for day, n in series.items() if day <= as_of}
    if not observed:
        raise ValueError(f"{project}: sin datos hasta {as_of}")
    for day, downloads in observed.items():
        totals[day.replace(day=1)] += downloads
    first_date = min(observed)
    monthly = _monthly(totals, first_date, as_of)
    closed = [m for m in monthly if m.status != "in_progress" and m.downloads is not None]
    return LibraryView(
        project=project,
        first_date=first_date,
        last_closed_month=closed[-1] if closed else None,
        monthly=monthly,
        yearly=_yearly(observed, first_date, as_of),
    )


def site_status(runs: Sequence[RunReport]) -> SiteStatus:
    """Última corrida aceptada y si la última de todas fue rechazada. `runs` va en orden."""
    good = [run for run in runs if run.status == "ok"]
    return SiteStatus(
        last_updated=good[-1].captured_at.date() if good else None,
        failed=bool(runs) and runs[-1].status == "failed",
    )
