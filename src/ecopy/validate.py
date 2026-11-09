"""Reglas de validación de una corrida, antes de escribir. Puras, sin E/S.

Umbrales medidos en `docs/spikes/s7-clickpy-revisiones-y-umbrales.md`: desde 2020 ningún día salió
de 0,529 a 1,494 respecto de los mismos días de semana previos.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import median

from ecopy.models import DailyDownload, DailySeries, DailyTotal, Problem, PythonMinorMonth
from ecopy.quality import DayQuality, day_quality

VOLUME_MIN = 0.4
VOLUME_MAX = 2.0
REFERENCE_WEEKS = 4
RECENT_DAYS = 30
"""Un backfill solo se compara en sus últimos días: la historia vieja tiene saltos conocidos."""
MIN_PRESENT = 0.98
MAX_PYTHON_DIFFERENCE = 0.005
MAX_STALE_DAYS = 3


@dataclass(frozen=True)
class Candidates:
    """Lo que una corrida quiere escribir."""

    totals: tuple[DailyTotal, ...] = ()
    downloads: tuple[DailyDownload, ...] = ()
    python: tuple[PythonMinorMonth, ...] = ()


@dataclass(frozen=True)
class History:
    """Lo que ya está guardado."""

    totals: DailySeries = field(default_factory=dict)
    last_days: Mapping[str, date] = field(default_factory=dict)


def _volume(totals: DailySeries, days: Sequence[date]) -> list[Problem]:
    problems = []
    for day in days:
        if day_quality(day) is not DayQuality.OK:
            continue
        previous = [day - timedelta(days=7 * k) for k in range(1, REFERENCE_WEEKS + 1)]
        reference = [totals[d] for d in previous if d in totals and day_quality(d) is DayQuality.OK]
        if len(reference) < REFERENCE_WEEKS:
            continue
        ratio = totals[day] / median(reference)
        if not VOLUME_MIN <= ratio <= VOLUME_MAX:
            problems.append(
                Problem("volume", "pypi_total_daily", f"{day}: {ratio:.2f} de lo normal")
            )
    return problems


def _presence(candidates: Candidates, history: History, projects: Sequence[str]) -> list[Problem]:
    seen: dict[str, date] = {}
    for row in candidates.downloads:
        seen[row.project] = max(row.date, seen.get(row.project, row.date))
    problems = [
        Problem("unknown_project", "downloads_daily", f"{p}: sin datos en la fuente")
        for p in projects
        if p not in seen and p not in history.last_days
    ]
    if not candidates.downloads:
        return problems
    newest = max(row.date for row in candidates.downloads)
    active_since = newest - timedelta(days=RECENT_DAYS)
    last_before: dict[str, date] = dict(history.last_days)
    for row in candidates.downloads:
        if row.date < newest:
            last_before[row.project] = max(row.date, last_before.get(row.project, row.date))
    expected = {p for p in projects if last_before.get(p, date.min) >= active_since}
    present = {row.project for row in candidates.downloads if row.date == newest}
    if expected and len(expected & present) / len(expected) < MIN_PRESENT:
        missing = sorted(expected - present)
        detail = f"{newest}: faltan {len(missing)} de {len(expected)}: {missing[:10]}"
        problems.append(Problem("missing_packages", "downloads_daily", detail))
    return problems


def _above_total(candidates: Candidates, totals: DailySeries) -> list[Problem]:
    over = [
        row for row in candidates.downloads if row.downloads > totals.get(row.date, row.downloads)
    ]
    if not over:
        return []
    first = over[0]
    detail = f"{len(over)} filas; p. ej. {first.project} el {first.date}: {first.downloads}"
    return [Problem("package_above_total", "downloads_daily", detail)]


def _python(candidates: Candidates, totals: DailySeries) -> list[Problem]:
    by_month: dict[date, int] = defaultdict(int)
    for row in candidates.python:
        by_month[row.month] += row.downloads
    month_totals: dict[date, int] = defaultdict(int)
    for day, downloads in totals.items():
        month_totals[day.replace(day=1)] += downloads
    problems = []
    for month, downloads in sorted(by_month.items()):
        total = month_totals.get(month)
        if total and abs(downloads - total) / total > MAX_PYTHON_DIFFERENCE:
            detail = f"{month:%Y-%m}: versiones {downloads} contra total {total}"
            problems.append(Problem("python_mismatch", "python_minor_monthly", detail))
    return problems


def _staleness(totals: DailySeries, as_of: date) -> list[Problem]:
    if not totals:
        return [Problem("stale", "pypi_total_daily", "no hay totales guardados ni nuevos")]
    newest = max(totals)
    if (as_of - newest).days > MAX_STALE_DAYS:
        return [Problem("stale", "pypi_total_daily", f"último día {newest}, se esperaba {as_of}")]
    return []


def check(
    candidates: Candidates, history: History, *, projects: Sequence[str], as_of: date
) -> list[Problem]:
    """Problemas que impiden aceptar la corrida; vacío si puede escribirse."""
    totals = {**history.totals, **{row.date: row.downloads for row in candidates.totals}}
    recent = sorted(row.date for row in candidates.totals)[-RECENT_DAYS:]
    return [
        *_volume(totals, recent),
        *_presence(candidates, history, projects),
        *_above_total(candidates, totals),
        *_python(candidates, totals),
        *_staleness(totals, as_of),
    ]
