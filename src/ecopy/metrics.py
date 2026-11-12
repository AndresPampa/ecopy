"""Métricas: funciones puras sobre las series, sin E/S."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from ecopy.catalog import FIRST_RANKED_YEAR, Catalog, PythonRelease
from ecopy.models import (
    CategoryPage,
    CategoryShare,
    Coverage,
    DailySeries,
    DomainPage,
    DomainShare,
    LibraryRow,
    LibraryView,
    MonthPoint,
    Mover,
    Newcomer,
    PeriodStatus,
    PythonVersionShare,
    ReleaseRow,
    ReleasesView,
    RunReport,
    SiteStatus,
    StarPoint,
    StarsView,
    TimelineEvent,
    VolumeView,
    YearShare,
    YearTotal,
    YearView,
)
from ecopy.quality import DISCONTINUITIES, SOURCE_START, period_coverage


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


def _monthly(
    totals: dict[date, int], first_date: date, as_of: date, pypi: Mapping[date, int]
) -> tuple[MonthPoint, ...]:
    points = []
    for month in _months(first_date.replace(day=1), as_of.replace(day=1)):
        end = _next_month(month) - timedelta(days=1)
        status, coverage = _period(month, end, first_date=first_date, as_of=as_of)
        downloads = totals.get(month)
        share = downloads / pypi[month] if downloads is not None and pypi.get(month) else None
        points.append(
            MonthPoint(
                month=month, downloads=downloads, status=status, coverage=coverage, share=share
            )
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


def _monthly_totals(daily: DailySeries, as_of: date) -> dict[date, int]:
    months: dict[date, int] = defaultdict(int)
    for day, downloads in daily.items():
        if day <= as_of:
            months[day.replace(day=1)] += downloads
    return months


def library_view(
    project: str,
    series: DailySeries,
    *,
    as_of: date,
    totals: DailySeries | None = None,
    catalog: Catalog | None = None,
    stars: StarsView | None = None,
) -> LibraryView:
    """La ficha de un paquete; `totals` agrega la cuota de PyPI y `catalog`, su lugar en él."""
    by_month: dict[date, int] = defaultdict(int)
    observed = {day: n for day, n in series.items() if day <= as_of}
    if not observed:
        raise ValueError(f"{project}: sin datos hasta {as_of}")
    start = catalog.series_start(project) if catalog is not None else None
    earlier = 0
    if start is not None and any(day >= start for day in observed):
        # Antes de la primera versión vigente, el nombre era de otra cosa: no es su historia.
        earlier = sum(n for day, n in observed.items() if day < start)
        observed = {day: n for day, n in observed.items() if day >= start}
    for day, downloads in observed.items():
        by_month[day.replace(day=1)] += downloads
    first_date = min(observed)
    monthly = _monthly(by_month, first_date, as_of, _monthly_totals(totals or {}, as_of))
    closed = [m for m in monthly if m.status != "in_progress" and m.downloads is not None]
    place = {}
    if catalog is not None:
        library = catalog.library(project)
        place = {
            "category": library.category,
            "domain": catalog.domain_of(library.category),
            "tags": library.tags,
            "repo": library.repo,
            "renamed_from": library.renamed_from,
            "renamed_to": catalog.renamed_to(project),
        }
    return LibraryView(
        project=project,
        first_date=first_date,
        earlier_downloads=earlier,
        last_closed_month=closed[-1] if closed else None,
        monthly=monthly,
        yearly=_yearly(observed, first_date, as_of),
        discontinuities=tuple(d for d in DISCONTINUITIES if first_date <= d <= as_of),
        stars=stars,
        **place,
    )


_TREND_MONTHS = 36


def _row(view: LibraryView) -> LibraryRow:
    closed = [m for m in view.monthly if m.status != "in_progress" and m.share is not None]
    last = view.last_closed_month
    return LibraryRow(
        project=view.project,
        category=view.category,
        domain=view.domain,
        tags=view.tags,
        month=last.month if last else None,
        downloads=last.downloads if last else None,
        trend=tuple(m.share for m in closed[-_TREND_MONTHS:]),
    )


def library_rows(views: Sequence[LibraryView]) -> tuple[LibraryRow, ...]:
    """Filas de los listados, de la más descargada a la menos en su último mes cerrado."""
    rows = [_row(view) for view in views]
    return tuple(sorted(rows, key=lambda r: (-(r.downloads or 0), r.project)))


def taxonomy_view(
    years: Sequence[YearView], rows: Sequence[LibraryRow], catalog: Catalog
) -> tuple[DomainPage, ...]:
    """Cuota por año de cada dominio y categoría, con las librerías de cada categoría.

    Dominios y categorías van de la mayor cuota del último año a la menor.
    """
    domain_share: dict[str, list[YearShare]] = defaultdict(list)
    category_share: dict[str, list[YearShare]] = defaultdict(list)
    for year in years:
        for domain in year.domains:
            domain_share[domain.slug].append(
                YearShare(year=year.year, status=year.status, share=domain.share)
            )
            for category in domain.categories:
                category_share[category.slug].append(
                    YearShare(year=year.year, status=year.status, share=category.share)
                )
    latest = years[-1].year if years else None

    def weight(shares: Sequence[YearShare]) -> float:
        """Cuota del último año; lo que ese año no tiene dato va al final."""
        return next((s.share for s in shares if s.year == latest), -1.0)

    pages = []
    for domain in catalog.domains():
        categories = [
            CategoryPage(
                slug=slug,
                domain=domain.slug,
                shares=tuple(category_share[slug]),
                rows=tuple(r for r in rows if r.category == slug),
            )
            for slug in domain.categories
        ]
        # sorted es estable: con la misma cuota queda el orden de la taxonomía.
        categories.sort(key=lambda c: -weight(c.shares))
        pages.append(
            DomainPage(
                slug=domain.slug,
                shares=tuple(domain_share[domain.slug]),
                categories=tuple(categories),
            )
        )
    pages.sort(key=lambda d: -weight(d.shares))
    return tuple(pages)


def releases_view(releases: Sequence[PythonRelease], *, as_of: date) -> ReleasesView:
    """Versiones de CPython, de la más nueva a la más vieja, con su estado a la fecha."""

    def row(release: PythonRelease) -> ReleaseRow:
        if release.end_of_life is None:
            status = "unknown"
        else:
            status = "supported" if release.end_of_life > as_of else "end_of_life"
        return ReleaseRow(
            version=release.version,
            released=release.released,
            end_of_life=release.end_of_life,
            status=status,
        )

    ordered = sorted(releases, key=lambda r: r.released, reverse=True)
    return ReleasesView(as_of=as_of, releases=tuple(row(r) for r in ordered))


def stars_view(
    repo: str,
    weeks: Mapping[date, int],
    counts: Mapping[date, int],
    *,
    shared_with: Sequence[str],
) -> StarsView:
    """Acumula las semanas netas; el total es el último conteo guardado, si lo hay."""
    running = 0
    points = []
    for week in sorted(weeks):
        running += weeks[week]
        points.append(StarPoint(week=week, stars=running))
    total = counts[max(counts)] if counts else running
    return StarsView(repo=repo, total=total, points=tuple(points), shared_with=tuple(shared_with))


def site_status(runs: Sequence[RunReport]) -> SiteStatus:
    """Última corrida aceptada y si la última de todas fue rechazada. `runs` va en orden."""
    good = [run for run in runs if run.status == "ok"]
    return SiteStatus(
        last_updated=good[-1].captured_at.date() if good else None,
        failed=bool(runs) and runs[-1].status == "failed",
    )


METHODOLOGY_VERSION = 1
"""Sube cuando cambia una fórmula o la taxonomía; los años ya congelados no se recalculan."""
_FOUNDATIONS = "foundations"
"""Dependencias que casi nadie instala a propósito: cuentan en cuotas, no en movers ni llegados."""
_MOVERS_PER_DIRECTION = 10


@dataclass(frozen=True)
class YearInputs:
    downloads: Mapping[str, DailySeries]
    totals: DailySeries
    python_minor: Mapping[date, Mapping[str, int]]
    catalog: Catalog


@dataclass(frozen=True)
class _Period:
    start: date
    end: date

    def __contains__(self, day: date) -> bool:
        return self.start <= day <= self.end


def _periods(year: int, as_of: date) -> tuple[_Period, _Period | None, bool]:
    """Período del año, el anterior con el que se compara y si el año está cerrado."""
    start, last = date(year, 1, 1), date(year, 12, 31)
    closed = last <= as_of
    period = _Period(start, last if closed else as_of)
    if year <= FIRST_RANKED_YEAR:
        return period, None, closed
    previous_start = date(year - 1, 1, 1)
    previous_end = date(year - 1, 12, 31) if closed else previous_start + (period.end - start)
    return period, _Period(previous_start, previous_end), closed


def _totals_by_project(
    downloads: Mapping[str, DailySeries], period: _Period | None
) -> dict[str, int]:
    if period is None:
        return {}
    totals = {
        project: sum(value for day, value in series.items() if day in period)
        for project, series in downloads.items()
    }
    return {project: total for project, total in totals.items() if total}


def _domains(current: Mapping[str, int], catalog: Catalog) -> tuple[DomainShare, ...]:
    grand_total = sum(current.values())
    by_category: dict[str, int] = defaultdict(int)
    for project, downloads in current.items():
        by_category[catalog.library(project).category] += downloads
    by_domain: dict[str, list[CategoryShare]] = defaultdict(list)
    for slug, downloads in sorted(by_category.items(), key=lambda kv: (-kv[1], kv[0])):
        share = CategoryShare(slug=slug, downloads=downloads, share=downloads / grand_total)
        by_domain[catalog.domain_of(slug)].append(share)
    domains = [
        DomainShare(
            slug=slug,
            downloads=sum(c.downloads for c in categories),
            share=sum(c.downloads for c in categories) / grand_total,
            categories=tuple(categories),
        )
        for slug, categories in by_domain.items()
    ]
    return tuple(sorted(domains, key=lambda d: (-d.downloads, d.slug)))


def _ranks(totals: Mapping[str, int], eligible: set[str]) -> dict[str, int]:
    ordered = sorted((p for p in totals if p in eligible), key=lambda p: (-totals[p], p))
    return {project: position for position, project in enumerate(ordered, start=1)}


def _movers(
    current: Mapping[str, int], previous: Mapping[str, int], catalog: Catalog
) -> tuple[tuple[Mover, ...], tuple[Mover, ...]]:
    if not previous:
        return (), ()
    current_total, previous_total = sum(current.values()), sum(previous.values())
    eligible = {p for p in {*current, *previous} if catalog.library(p).category != _FOUNDATIONS}
    now, before = _ranks(current, eligible), _ranks(previous, eligible)
    movers = []
    for project in eligible:
        share = current.get(project, 0) / current_total
        rank, earlier = now.get(project), before.get(project)
        movers.append(
            Mover(
                project=project,
                category=catalog.library(project).category,
                share=share,
                share_change=100 * (share - previous.get(project, 0) / previous_total),
                rank=rank,
                rank_change=earlier - rank if rank and earlier else None,
            )
        )
    movers.sort(key=lambda m: (-m.share_change, m.project))
    up = tuple(m for m in movers if m.share_change > 0)[:_MOVERS_PER_DIRECTION]
    down = tuple(m for m in reversed(movers) if m.share_change < 0)[:_MOVERS_PER_DIRECTION]
    return up, down


def _newcomers(year: int, catalog: Catalog) -> tuple[Newcomer, ...]:
    if year <= FIRST_RANKED_YEAR:
        return ()
    earlier = {p for y in range(FIRST_RANKED_YEAR, year) for p in catalog.top(y)}
    newcomers = []
    for position, project in enumerate(catalog.top(year), start=1):
        library = catalog.library(project)
        is_new = project not in earlier and library.renamed_from not in earlier
        if is_new and library.category != _FOUNDATIONS:
            newcomers.append(Newcomer(project=project, category=library.category, rank=position))
    return tuple(newcomers)


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _python_shares(
    minors: Mapping[date, Mapping[str, int]], period: _Period, catalog: Catalog
) -> tuple[tuple[PythonVersionShare, ...], float, float]:
    """Versiones reales de CPython, y las fracciones sin versión y de valores que no lo son."""
    totals: dict[str, int] = defaultdict(int)
    for month, values in minors.items():
        closed = month >= period.start and _next_month(month) - timedelta(days=1) <= period.end
        if closed:
            for minor, downloads in values.items():
                totals[minor] += downloads
    grand_total = sum(totals.values())
    if not grand_total:
        return (), 0.0, 0.0
    real = {r.version for r in catalog.python_releases()}
    valid = {minor: n for minor, n in totals.items() if minor in real}
    valid_total = sum(valid.values())
    versions = tuple(
        PythonVersionShare(version=minor, downloads=n, share=n / valid_total)
        for minor, n in sorted(valid.items(), key=lambda kv: _version_key(kv[0]), reverse=True)
    )
    unknown = totals.get("", 0)
    return versions, unknown / grand_total, (grand_total - valid_total - unknown) / grand_total


def _timeline(period: _Period, catalog: Catalog) -> tuple[TimelineEvent, ...]:
    events = []
    for release in catalog.python_releases():
        if release.released in period:
            events.append(
                TimelineEvent(date=release.released, version=release.version, kind="release")
            )
        if release.end_of_life and release.end_of_life in period:
            events.append(
                TimelineEvent(date=release.end_of_life, version=release.version, kind="end_of_life")
            )
    return tuple(sorted(events, key=lambda e: (e.date, e.version)))


def _volume(totals: DailySeries, period: _Period, previous: _Period | None) -> VolumeView:
    total = sum(value for day, value in totals.items() if day in period)
    before = sum(value for day, value in totals.items() if day in previous) if previous else None
    crosses = previous is not None and any(
        previous.start < d <= period.end for d in DISCONTINUITIES
    )
    growth = None if crosses or not before else (total - before) / before
    return VolumeView(
        total=total,
        previous=before or None,
        growth=growth,
        discontinuities=tuple(d for d in DISCONTINUITIES if d in period),
    )


def year_view(year: int, inputs: YearInputs, *, as_of: date) -> YearView:
    """La vista de un año, desde 2017, a la fecha `as_of`."""
    if not FIRST_RANKED_YEAR <= year <= as_of.year:
        raise ValueError(f"año fuera de rango: {year}")
    period, previous, closed = _periods(year, as_of)
    current = _totals_by_project(inputs.downloads, period)
    if not current:
        raise ValueError(f"sin datos en {year}")
    earlier = _totals_by_project(inputs.downloads, previous)
    volume = _volume(inputs.totals, period, previous)
    up, down = _movers(current, earlier, inputs.catalog)
    versions, unknown, other = _python_shares(inputs.python_minor, period, inputs.catalog)
    return YearView(
        year=year,
        status="closed" if closed else "ytd",
        methodology_version=METHODOLOGY_VERSION,
        period_start=period.start,
        period_end=period.end,
        previous_start=previous.start if previous else None,
        previous_end=previous.end if previous else None,
        coverage=period_coverage(period.start, period.end),
        volume=volume,
        catalog_share=sum(current.values()) / volume.total if volume.total else 0.0,
        domains=_domains(current, inputs.catalog),
        movers_up=up,
        movers_down=down,
        newcomers=_newcomers(year, inputs.catalog),
        python_versions=versions,
        python_unknown_share=unknown,
        python_other_share=other,
        timeline=_timeline(period, inputs.catalog),
    )
