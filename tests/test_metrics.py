"""Métricas de la ficha de una librería: funciones puras sobre la serie diaria."""

from datetime import date, timedelta
from itertools import pairwise

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from ecopy.metrics import library_view


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


def partial_flags(as_of: date) -> list[tuple[date, bool]]:
    view = library_view("fastapi", {date(2024, 1, 15): 1, date(2024, 2, 1): 2}, as_of=as_of)
    return [(m.month, m.partial) for m in view.monthly]


def test_the_month_in_progress_is_marked_partial():
    assert partial_flags(date(2024, 2, 10)) == [
        (date(2024, 1, 1), False),
        (date(2024, 2, 1), True),
    ]


def test_a_month_ending_on_as_of_is_complete():
    assert partial_flags(date(2024, 2, 29)) == [
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
    return [(y.year, y.downloads, y.partial, y.ytd) for y in view.yearly]


def test_yearly_totals_mark_2016_partial_and_the_current_year_as_ytd():
    series = {
        date(2016, 6, 1): 1,
        date(2017, 6, 1): 2,
        date(2017, 7, 1): 3,
        date(2024, 3, 1): 4,
    }

    assert yearly(series, date(2024, 3, 15)) == [
        (2016, 1, True, False),
        (2017, 5, False, False),
        (2024, 4, False, True),
    ]


def test_a_year_ending_on_as_of_is_not_ytd():
    assert yearly({date(2024, 3, 1): 4}, date(2024, 12, 31)) == [(2024, 4, False, False)]


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
def test_at_most_the_last_month_is_partial(series, as_of):
    observed_up_to(series, as_of)

    months = library_view("p", series, as_of=as_of).monthly

    assert not any(m.partial for m in months[:-1])


@given(SERIES, DAYS)
def test_2016_is_always_partial(series, as_of):
    observed_up_to(series, as_of)

    for total in library_view("p", series, as_of=as_of).yearly:
        assert total.partial == (total.year == 2016)


@given(SERIES, DAYS, st.integers(1, 400))
def test_a_past_view_does_not_change_when_later_data_arrives(series, as_of, days_later):
    observed_up_to(series, as_of)
    later = {**series, as_of + timedelta(days=days_later): 123}

    assert library_view("p", later, as_of=as_of) == library_view("p", series, as_of=as_of)
