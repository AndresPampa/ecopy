"""Ingesta: decide qué pedir, valida antes de escribir y deja registro de la corrida."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from ecopy.models import (
    Batch,
    DailyDownload,
    DailyTotal,
    DatasetCounts,
    Problem,
    PythonMinorMonth,
    Run,
    RunReport,
    StarsReport,
    StarTotal,
    StarTotalsBatch,
    StarWeek,
    StarWeeksBatch,
)
from ecopy.quality import SOURCE_START
from ecopy.sources.clickpy import ClickPy, SourceError
from ecopy.sources.github import BudgetExhausted, GitHub, RateLimited
from ecopy.store import Store
from ecopy.validate import RECENT_DAYS, Candidates, History, check

REOBSERVE_DAYS = 7

Acquisition = Literal["backfill", "observed"]


@dataclass(frozen=True)
class _Planned:
    batch: Batch
    dataset: str
    acquisition: Acquisition


def python_cutoff(end: date) -> date:
    """Primer día del primer mes que `end` no llega a cerrar."""
    return (end + timedelta(days=1)).replace(day=1)


def _window_start(last_saved: date, reobserve_days: int) -> date:
    return last_saved - timedelta(days=reobserve_days - 1)


def _fetch_downloads(
    projects: Sequence[str], source: ClickPy, last_days: dict[str, date], end: date, reobserve: int
) -> list[_Planned]:
    new = [p for p in projects if p not in last_days]
    known = [p for p in projects if p in last_days]
    planned = []
    if new:
        batch = source.daily_downloads(new, SOURCE_START, end)
        planned.append(_Planned(batch, "downloads_daily", "backfill"))
    if known:
        # Ancla común: un paquete sin descargas desde hace años no arrastra a los demás.
        start = _window_start(max(last_days[p] for p in known), reobserve)
        if start <= end:
            batch = source.daily_downloads(known, start, end)
            planned.append(_Planned(batch, "downloads_daily", "observed"))
    return planned


def _fetch_totals(source: ClickPy, saved: dict[date, int], end: date, reobserve: int) -> _Planned:
    if not saved:
        return _Planned(source.pypi_daily_totals(SOURCE_START, end), "pypi_total_daily", "backfill")
    start = min(_window_start(max(saved), reobserve), end)
    return _Planned(source.pypi_daily_totals(start, end), "pypi_total_daily", "observed")


def _fetch_python(source: ClickPy, saved: dict, end: date) -> _Planned | None:
    """Cada pasada lee toda la tabla: solo se trae cuando falta un mes cerrado."""
    cutoff = python_cutoff(end)
    last_closed = (cutoff - timedelta(days=1)).replace(day=1)
    if saved and max(saved) >= last_closed:
        return None
    acquisition: Acquisition = "observed" if saved else "backfill"
    return _Planned(source.python_minor_monthly(before=cutoff), "python_minor_monthly", acquisition)


def _candidates(planned: Sequence[_Planned]) -> Candidates:
    rows: dict[str, list] = defaultdict(list)
    for item in planned:
        rows[item.dataset].extend(item.batch.rows)
    return Candidates(
        totals=tuple(rows["pypi_total_daily"]),
        downloads=tuple(rows["downloads_daily"]),
        python=tuple(rows["python_minor_monthly"]),
    )


def ingest(
    projects: Sequence[str],
    source: ClickPy,
    store: Store,
    *,
    now: datetime,
    reobserve_days: int = REOBSERVE_DAYS,
) -> RunReport:
    """Trae lo que falta y lo escribe si pasa la validación. Nunca deja datos rechazados."""
    captured = now.astimezone(UTC)
    report_id = f"{captured:%Y%m%dT%H%M%SZ}"
    end = captured.date() - timedelta(days=1)
    totals = store.pypi_daily_totals()
    last_days = store.last_days()

    def finish(
        status: Literal["ok", "failed"],
        problems: Sequence[Problem] = (),
        datasets: dict[str, DatasetCounts] | None = None,
        last_day: date | None = None,
    ) -> RunReport:
        last_day = last_day or max(totals, default=None)
        report = RunReport(report_id, captured, status, tuple(problems), datasets or {}, last_day)
        store.record_run(report)
        return report

    def attempt() -> RunReport:
        planned = [
            *_fetch_downloads(projects, source, last_days, end, reobserve_days),
            _fetch_totals(source, totals, end, reobserve_days),
        ]
        python = _fetch_python(source, store.python_minor_monthly(), end)
        if python:
            planned.append(python)

        candidates = _candidates(planned)
        problems = check(candidates, History(totals, last_days), projects=projects, as_of=end)
        if problems:
            return finish("failed", problems)

        counts: dict[str, DatasetCounts] = {}
        for item in planned:
            run = Run(f"{report_id}-{item.acquisition}", captured, item.acquisition)
            result = store.append(item.batch, run)
            previous = counts.get(item.dataset, DatasetCounts(0, 0))
            counts[item.dataset] = DatasetCounts(
                previous.new_rows + result.new_rows, previous.revised_rows + result.revised_rows
            )
        newest = max([*totals, *(row.date for row in candidates.totals)], default=None)
        return finish("ok", datasets=counts, last_day=newest)

    try:
        return attempt()
    except SourceError as error:
        return finish("failed", [Problem("source_error", "", str(error))])
    except Exception as error:
        # Sin este registro el sitio no mostraría "Actualización fallida" (auditoría run-1).
        finish("failed", [Problem("internal_error", "", repr(error))])
        raise


def validate_store(projects: Sequence[str], store: Store, *, now: datetime) -> list[Problem]:
    """Aplica las reglas de la corrida a los últimos días guardados."""
    as_of = now.astimezone(UTC).date() - timedelta(days=1)
    totals = store.pypi_daily_totals()
    recent = sorted(totals)[-RECENT_DAYS:]
    first = recent[0] if recent else date.max
    series = store.daily_downloads(projects)
    downloads = tuple(
        DailyDownload(project, day, value)
        for project, days in series.items()
        for day, value in days.items()
        if day >= first
    )
    python = tuple(
        PythonMinorMonth(month, minor, value)
        for month, minors in store.python_minor_monthly().items()
        for minor, value in minors.items()
    )
    candidates = Candidates(
        totals=tuple(DailyTotal(day, totals[day]) for day in recent),
        downloads=downloads,
        python=python,
    )
    return check(candidates, History(totals, store.last_days()), projects=projects, as_of=as_of)


def ingest_stars(
    repos: Sequence[str], source: GitHub, store: Store, *, now: datetime
) -> StarsReport:
    """Completa la historia de los repos que no la tienen y actualiza los demás.

    Guarda una vez por corrida, aun si se interrumpe, y solo repos completos: la siguiente
    corrida retoma por los que falten.
    """
    captured = now.astimezone(UTC)
    report_id = f"{captured:%Y%m%dT%H%M%SZ}"
    done = store.backfilled_repos()
    plan = [(r, "backfill") for r in repos if r not in done]
    plan += [(r, "observed") for r in repos if r in done]
    weeks: dict[str, list[StarWeek]] = {"backfill": [], "observed": []}
    totals: dict[str, list[StarTotal]] = {"backfill": [], "observed": []}
    finished: dict[str, list[str]] = {"backfill": [], "observed": []}
    failed: list[tuple[str, str]] = []
    moved: list[tuple[str, str]] = []
    stopped: str | None = None
    attempted = 0

    def save() -> None:
        for kind in ("backfill", "observed"):
            run = Run(f"{report_id}-{kind}", captured, kind)
            store.append(StarWeeksBatch("github", tuple(weeks[kind])), run)
            store.append(StarTotalsBatch("github", tuple(totals[kind])), run)

    try:
        for repo, kind in plan:
            fetch = source.full_history if kind == "backfill" else source.recent
            try:
                stars = fetch(repo)
            except BudgetExhausted:
                stopped = "budget"
                break
            except RateLimited:
                stopped = "rate_limited"
                break
            except SourceError as error:
                attempted += 1
                failed.append((repo, str(error)))
                continue
            attempted += 1
            weeks[kind].extend(stars.weeks)
            totals[kind].append(StarTotal(repo, captured.date(), stars.stars))
            finished[kind].append(repo)
            if stars.full_name.lower() != repo.lower():
                moved.append((repo, stars.full_name))
    finally:
        save()

    report = StarsReport(
        id=report_id,
        captured_at=captured,
        status="complete" if stopped is None and not failed else "partial",
        requests=source.requests,
        backfilled=tuple(finished["backfill"]),
        updated=tuple(finished["observed"]),
        pending=len(plan) - attempted,
        failed=tuple(failed),
        moved=tuple(moved),
        stopped=stopped,
    )
    store.record_stars_run(report)
    return report
