"""Reglas de validación: qué corridas se rechazan antes de escribir."""

from datetime import date, timedelta

from ecopy.models import DailyDownload, DailyTotal, PythonMinorMonth
from ecopy.validate import Candidates, History, check

DAY = date(2024, 6, 28)  # viernes
AS_OF = DAY


def history_totals(level: int = 1000) -> dict[date, int]:
    """Cuatro semanas previas a DAY con volumen constante."""
    return {DAY - timedelta(days=offset): level for offset in range(1, 40)}


def codes(candidates: Candidates, history: History | None = None, **kwargs) -> list[str]:
    history = history or History(totals=history_totals(), last_days={})
    options = {"projects": (), "as_of": AS_OF, **kwargs}
    return [problem.code for problem in check(candidates, history, **options)]


def totals(value: int, day: date = DAY) -> tuple[DailyTotal, ...]:
    return (DailyTotal(day, value),)


def test_a_normal_day_has_no_problems():
    assert codes(Candidates(totals=totals(1000))) == []


def test_a_day_at_the_lower_limit_passes_and_below_it_is_rejected():
    assert codes(Candidates(totals=totals(400))) == []
    assert codes(Candidates(totals=totals(399))) == ["volume"]


def test_a_day_at_the_upper_limit_passes_and_above_it_is_rejected():
    assert codes(Candidates(totals=totals(2000))) == []
    assert codes(Candidates(totals=totals(2001))) == ["volume"]


def test_volume_needs_four_previous_comparable_days():
    history = History(totals={DAY - timedelta(days=7): 1000}, last_days={})

    assert codes(Candidates(totals=totals(1)), history) == []


def test_known_degraded_days_are_not_rejected_nor_used_as_reference():
    degraded = date(2018, 7, 24)
    reference = {degraded - timedelta(days=7 * k): 1000 for k in range(1, 5)}
    history = History(totals=reference, last_days={})

    assert codes(Candidates(totals=totals(1, degraded)), history, as_of=degraded) == []


def test_only_recent_days_of_a_large_backfill_are_checked_for_volume():
    old = DAY - timedelta(days=200)
    reference = {old - timedelta(days=7 * k): 1000 for k in range(1, 5)}
    recent = tuple(DailyTotal(DAY - timedelta(days=d), 1000) for d in range(30))
    candidates = Candidates(totals=(DailyTotal(old, 1), *recent[::-1]))
    history = History(totals=reference, last_days={})

    assert codes(candidates, history) == []


def rows(day: date, *projects: str) -> tuple[DailyDownload, ...]:
    return tuple(DailyDownload(p, day, 1) for p in projects)


def names(count: int) -> tuple[str, ...]:
    return tuple(f"p{i:03}" for i in range(count))


def test_at_least_98_percent_of_the_expected_packages_must_be_present():
    expected = names(100)
    history = History(history_totals(), {p: DAY - timedelta(days=1) for p in expected})
    base = totals(1000)

    enough = Candidates(totals=base, downloads=rows(DAY, *expected[:98]))
    short = Candidates(totals=base, downloads=rows(DAY, *expected[:97]))

    assert codes(enough, history, projects=expected) == []
    assert codes(short, history, projects=expected) == ["missing_packages"]


def test_packages_dormant_for_over_a_month_are_not_expected():
    history = History(
        history_totals(),
        {"alive": DAY - timedelta(days=1), "dormant": DAY - timedelta(days=31)},
    )
    candidates = Candidates(totals=totals(1000), downloads=rows(DAY, "alive"))

    assert codes(candidates, history, projects=("alive", "dormant")) == []


def test_a_backfill_expects_the_packages_seen_before_its_last_day():
    earlier = DAY - timedelta(days=1)
    candidates = Candidates(
        totals=totals(1000),
        downloads=(*rows(earlier, "a", "b"), *rows(DAY, "a")),
    )

    assert codes(candidates, projects=("a", "b")) == ["missing_packages"]


def test_a_requested_package_without_any_data_is_rejected():
    candidates = Candidates(totals=totals(1000), downloads=rows(DAY, "a"))

    assert codes(candidates, projects=("a", "typo")) == ["unknown_project"]


def test_a_package_above_the_total_of_its_day_is_rejected():
    candidates = Candidates(
        totals=totals(1000),
        downloads=(DailyDownload("a", DAY, 1001),),
    )

    assert codes(candidates, projects=("a",)) == ["package_above_total"]


def january_total(value: int) -> dict[date, int]:
    days = [date(2024, 1, d) for d in range(1, 32)]
    return {d: value // 31 for d in days}


def versions(value: int) -> tuple[PythonMinorMonth, ...]:
    return (PythonMinorMonth(date(2024, 1, 1), "3.12", value),)


def test_python_versions_must_match_the_monthly_total_within_half_a_percent():
    history = History(january_total(31_000), {})
    as_of = date(2024, 1, 31)

    assert codes(Candidates(python=versions(31_155)), history, as_of=as_of) == []
    assert codes(Candidates(python=versions(31_156)), history, as_of=as_of) == ["python_mismatch"]


def test_a_month_without_totals_is_not_compared():
    history = History(january_total(31_000), {})
    feb = (PythonMinorMonth(date(2024, 2, 1), "3.12", 5),)

    assert codes(Candidates(python=feb), history, as_of=date(2024, 1, 31)) == []


def test_data_older_than_three_days_is_stale():
    history = History(totals={DAY: 1000}, last_days={})

    assert codes(Candidates(), history, as_of=DAY + timedelta(days=3)) == []
    assert codes(Candidates(), history, as_of=DAY + timedelta(days=4)) == ["stale"]


def test_no_totals_at_all_is_stale():
    assert codes(Candidates(), History(totals={}, last_days={})) == ["stale"]


def test_a_known_degraded_day_with_good_references_is_accepted():
    degraded = date(2018, 4, 17)
    reference = {degraded - timedelta(days=7 * k): 1000 for k in range(1, 5)}
    history = History(totals=reference, last_days={})

    assert codes(Candidates(totals=totals(1, degraded)), history, as_of=degraded) == []
