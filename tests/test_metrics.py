"""Métricas de la ficha de una librería: funciones puras sobre la serie diaria."""

from datetime import UTC, date, datetime, timedelta
from itertools import pairwise

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from ecopy.metrics import library_view, site_status
from ecopy.models import RunReport, SiteStatus


def test_daily_downloads_are_summed_by_month():
    view = library_view(
        "fastapi",
        {date(2024, 1, 1): 10, date(2024, 1, 31): 5, date(2024, 2, 1): 7},
        as_of=date(2024, 2, 29),
    )

    assert view.project == "fastapi"
    assert [(m.month, m.downloads) for m in view.monthly] == [
        (date(2024, 1, 1), 15),
        (date(2024, 2, 1), 7),
    ]


def test_days_after_as_of_are_ignored():
    view = library_view(
        "fastapi",
        {date(2024, 1, 31): 5, date(2024, 2, 1): 7},
        as_of=date(2024, 1, 31),
    )

    assert [(m.month, m.downloads) for m in view.monthly] == [(date(2024, 1, 1), 5)]


def in_progress_flags(as_of: date) -> list[tuple[date, bool]]:
    view = library_view("fastapi", {date(2024, 1, 1): 1, date(2024, 2, 1): 2}, as_of=as_of)
    return [(m.month, m.status == "in_progress") for m in view.monthly]


def test_the_month_in_progress_is_marked():
    assert in_progress_flags(date(2024, 2, 10)) == [
        (date(2024, 1, 1), False),
        (date(2024, 2, 1), True),
    ]


def test_a_month_ending_on_as_of_is_not_in_progress():
    assert in_progress_flags(date(2024, 2, 29)) == [
        (date(2024, 1, 1), False),
        (date(2024, 2, 1), False),
    ]


def test_months_without_data_stay_as_gaps_up_to_as_of():
    view = library_view(
        "fastapi",
        {date(2016, 2, 1): 3, date(2016, 5, 22): 4},
        as_of=date(2016, 6, 30),
    )

    assert [(m.month, m.downloads) for m in view.monthly] == [
        (date(2016, 2, 1), 3),
        (date(2016, 3, 1), None),
        (date(2016, 4, 1), None),
        (date(2016, 5, 1), 4),
        (date(2016, 6, 1), None),
    ]


def yearly(series, as_of):
    view = library_view("fastapi", series, as_of=as_of)
    return [(y.year, y.downloads, y.status) for y in view.yearly]


def test_yearly_totals_carry_the_status_of_each_year():
    series = {
        date(2016, 1, 22): 1,
        date(2017, 6, 1): 2,
        date(2017, 7, 1): 3,
        date(2024, 3, 1): 4,
    }

    assert yearly(series, date(2024, 3, 15)) == [
        (2016, 1, "source_gap"),
        (2017, 5, "degraded"),  # 2017-05-11
        (2024, 4, "in_progress"),
    ]


def statuses(series, as_of):
    view = library_view("p", series, as_of=as_of)
    return view.monthly, view.yearly


def test_the_first_year_of_a_package_is_not_complete():
    fastapi = {date(2018, 12, 8): 1, date(2019, 1, 1): 2, date(2020, 6, 1): 3}

    _, years = statuses(fastapi, date(2020, 12, 31))

    assert [(y.year, y.status) for y in years] == [
        (2018, "package_start"),
        (2019, "source_gap"),
        (2020, "complete"),
    ]


def test_a_package_starting_on_the_first_day_of_a_period_has_no_start_status():
    months, years = statuses({date(2020, 1, 1): 1, date(2020, 2, 1): 2}, date(2020, 12, 31))

    assert months[0].status == "complete"
    assert years[0].status == "complete"


def test_the_first_day_of_the_source_is_not_the_start_of_a_package():
    months, _ = statuses({date(2016, 1, 22): 1, date(2016, 2, 1): 2}, date(2016, 2, 29))

    assert [m.status for m in months] == ["source_gap", "complete"]


def test_the_first_month_of_a_package_is_marked():
    months, _ = statuses({date(2024, 3, 15): 1, date(2024, 4, 1): 2}, date(2024, 4, 30))

    assert [m.status for m in months] == ["package_start", "complete"]


def test_source_gaps_and_degraded_windows_mark_their_months():
    series = {date(2018, 6, 1): 1, date(2018, 7, 1): 1, date(2018, 8, 1): 1}
    months, _ = statuses(series, date(2018, 8, 31))
    assert [m.status for m in months] == ["complete", "degraded", "complete"]

    months, _ = statuses({date(2019, 3, 1): 1, date(2019, 4, 1): 1}, date(2019, 4, 30))
    assert months[1].status == "source_gap"
    assert (months[1].coverage.expected, months[1].coverage.with_data) == (30, 28)


def test_a_day_without_rows_of_a_package_does_not_change_a_normal_month():
    months, _ = statuses({date(2024, 1, 1): 1, date(2024, 1, 31): 1}, date(2024, 1, 31))

    assert months[0].status == "complete"


def test_coverage_counts_from_the_first_day_of_the_package_and_up_to_as_of():
    months, years = statuses({date(2024, 3, 15): 1}, date(2024, 3, 20))

    assert months[0].coverage.expected == 6
    assert years[0].coverage.expected == 6


def test_a_year_ending_on_as_of_is_not_ytd():
    assert yearly({date(2024, 1, 1): 4}, date(2024, 12, 31)) == [(2024, 4, "complete")]


def test_first_date_and_last_closed_month_with_data():
    view = library_view(
        "fastapi",
        {date(2023, 12, 8): 1, date(2024, 1, 5): 2, date(2024, 3, 5): 3},
        as_of=date(2024, 3, 10),
    )

    assert view.first_date == date(2023, 12, 8)
    assert view.last_closed_month.month == date(2024, 1, 1)  # febrero es un hueco; marzo, en curso
    assert view.last_closed_month.downloads == 2


def test_last_closed_month_is_none_when_no_month_has_closed():
    view = library_view("fastapi", {date(2024, 3, 5): 3}, as_of=date(2024, 3, 10))

    assert view.last_closed_month is None


def test_a_series_without_data_up_to_as_of_is_rejected():
    with pytest.raises(ValueError, match="sin datos"):
        library_view("fastapi", {date(2024, 3, 5): 3}, as_of=date(2024, 3, 1))


DAYS = st.dates(date(2016, 1, 22), date(2026, 12, 31))
SERIES = st.dictionaries(DAYS, st.integers(0, 10**10), min_size=1, max_size=200)


def observed_up_to(series, as_of):
    observed = {d: n for d, n in series.items() if d <= as_of}
    assume(observed)
    return observed


@given(SERIES, DAYS)
def test_monthly_and_yearly_totals_add_up_to_the_daily_series(series, as_of):
    observed = observed_up_to(series, as_of)

    view = library_view("p", series, as_of=as_of)

    assert sum(m.downloads or 0 for m in view.monthly) == sum(observed.values())
    assert sum(y.downloads for y in view.yearly) == sum(observed.values())


@given(SERIES, DAYS)
def test_months_are_contiguous_and_end_at_as_of(series, as_of):
    first = min(observed_up_to(series, as_of))

    months = [m.month for m in library_view("p", series, as_of=as_of).monthly]

    assert months[0] == first.replace(day=1)
    assert months[-1] == as_of.replace(day=1)
    for current, following in pairwise(months):
        assert following == (current + timedelta(days=32)).replace(day=1)


@given(SERIES, DAYS)
def test_at_most_the_last_month_is_in_progress(series, as_of):
    observed_up_to(series, as_of)

    months = library_view("p", series, as_of=as_of).monthly

    assert not any(m.status == "in_progress" for m in months[:-1])


@given(SERIES, DAYS)
def test_2016_is_never_complete(series, as_of):
    observed_up_to(series, as_of)

    for total in library_view("p", series, as_of=as_of).yearly:
        if total.year == 2016:
            assert total.status != "complete"


@given(SERIES, DAYS, st.integers(1, 400))
def test_a_past_view_does_not_change_when_later_data_arrives(series, as_of, days_later):
    observed_up_to(series, as_of)
    later = {**series, as_of + timedelta(days=days_later): 123}

    assert library_view("p", later, as_of=as_of) == library_view("p", series, as_of=as_of)


def report(hour: int, status: str, *, last_day: date | None = date(2024, 1, 31)) -> RunReport:
    return RunReport(
        id=f"run{hour}",
        captured_at=datetime(2024, 2, 1, hour, tzinfo=UTC),
        status=status,
        problems=(),
        datasets={},
        last_day=last_day,
    )


def test_site_status_without_runs_shows_nothing():
    assert site_status(()) == SiteStatus(last_updated=None, failed=False)


def test_site_status_of_a_healthy_run():
    assert site_status((report(1, "ok"),)) == SiteStatus(date(2024, 2, 1), failed=False)


def test_a_failed_last_run_keeps_the_date_of_the_last_good_one():
    runs = (report(1, "ok"), report(2, "failed"))
    assert site_status(runs) == SiteStatus(date(2024, 2, 1), failed=True)


def test_a_good_run_after_a_failure_clears_the_notice():
    assert site_status((report(1, "failed"), report(2, "ok"))).failed is False


def test_a_failure_without_previous_good_runs_has_no_date():
    assert site_status((report(1, "failed"),)) == SiteStatus(None, failed=True)


def test_a_library_view_lists_the_discontinuities_inside_its_history():
    series = {date(2018, 7, 1): 5, date(2019, 1, 1): 5}

    assert library_view("a", series, as_of=date(2019, 1, 1)).discontinuities == (date(2018, 7, 27),)
    assert library_view("a", {date(2019, 1, 1): 5}, as_of=date(2019, 1, 2)).discontinuities == ()
