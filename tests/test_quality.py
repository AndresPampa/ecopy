"""Calendario de calidad de la fuente: qué días tienen huecos o están degradados."""

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ecopy.quality import DayQuality, day_quality, period_coverage


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2016, 1, 21), DayQuality.GAP),  # anterior al primer día de la fuente
        (date(2016, 1, 22), DayQuality.OK),
        (date(2016, 3, 5), DayQuality.OK),
        (date(2016, 3, 6), DayQuality.GAP),
        (date(2016, 5, 21), DayQuality.GAP),
        (date(2016, 5, 22), DayQuality.OK),
        (date(2018, 7, 10), DayQuality.OK),
        (date(2018, 7, 11), DayQuality.DEGRADED),
        (date(2018, 7, 26), DayQuality.DEGRADED),
        (date(2018, 7, 27), DayQuality.OK),
        (date(2019, 4, 25), DayQuality.DEGRADED),
        (date(2019, 4, 26), DayQuality.GAP),
        (date(2019, 4, 27), DayQuality.GAP),
        (date(2019, 4, 28), DayQuality.DEGRADED),
        (date(2016, 12, 8), DayQuality.DEGRADED),
        (date(2017, 5, 11), DayQuality.DEGRADED),
        (date(2018, 4, 17), DayQuality.DEGRADED),
        (date(2019, 4, 13), DayQuality.DEGRADED),
        (date(2026, 8, 28), DayQuality.OK),  # caída sin explicar, no cumple la regla
    ],
)
def test_known_days_are_classified_at_the_edges_of_each_window(day, expected):
    assert day_quality(day) is expected


def test_coverage_counts_gaps_and_degraded_days_of_a_period():
    coverage = period_coverage(date(2019, 4, 1), date(2019, 4, 30))

    assert (coverage.expected, coverage.gap, coverage.degraded) == (30, 2, 3)
    assert coverage.with_data == 28


days = st.dates(date(2015, 12, 1), date(2027, 1, 31))


@given(days, days)
def test_every_day_of_a_period_is_counted_once(first, last):
    first, last = min(first, last), max(first, last)

    coverage = period_coverage(first, last)

    assert coverage.expected == (last - first).days + 1
    assert 0 <= coverage.gap + coverage.degraded <= coverage.expected
