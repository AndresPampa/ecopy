"""Vista anual: función pura sobre las series, el catálogo y `as_of`."""

from datetime import date, timedelta

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from ecopy.catalog import Catalog, Library, PythonRelease
from ecopy.metrics import YearInputs, year_view

DOMAINS = {"web": "development", "testing": "development", "foundations": "infrastructure"}
RELEASES = (
    PythonRelease("2.7", date(2010, 7, 3), date(2020, 1, 1)),
    PythonRelease("3.9", date(2020, 10, 5), date(2025, 10, 31)),
    PythonRelease("3.10", date(2021, 10, 4), date(2026, 10, 1)),
    PythonRelease("3.12", date(2023, 10, 2), date(2028, 10, 31)),
)


def library(project: str, category: str, renamed_from: str | None = None) -> Library:
    return Library(project, category, (), None, renamed_from)


LIBRARIES = {
    "django": library("django", "web"),
    "flask": library("flask", "web"),
    "pytest": library("pytest", "testing"),
    "six": library("six", "foundations"),
    "newname": library("newname", "web", renamed_from="oldname"),
    "oldname": library("oldname", "web"),
}


def catalog(top=None) -> Catalog:
    return Catalog(LIBRARIES, DOMAINS, top=top or {}, releases=RELEASES)


def yearly(values: dict[int, int], *, day: tuple[int, int] = (6, 1)) -> dict[date, int]:
    return {date(year, *day): value for year, value in values.items()}


def inputs(downloads, *, totals=None, python=None, top=None) -> YearInputs:
    if totals is None:
        by_day: dict[date, int] = {}
        for series in downloads.values():
            for day, value in series.items():
                by_day[day] = by_day.get(day, 0) + value
        totals = by_day
    return YearInputs(downloads, totals, python or {}, catalog(top))


BASIC = {
    "django": yearly({2023: 30, 2024: 60}),
    "flask": yearly({2023: 10, 2024: 20}),
    "pytest": yearly({2023: 10, 2024: 10}),
    "six": yearly({2023: 50, 2024: 10}),
}
CLOSED = date(2024, 12, 31)


def test_a_closed_year_uses_the_whole_calendar_year():
    view = year_view(2023, inputs(BASIC), as_of=CLOSED)

    assert view.status == "closed"
    assert (view.period_start, view.period_end) == (date(2023, 1, 1), date(2023, 12, 31))
    assert view.methodology_version == 1


def test_category_and_domain_shares_are_over_the_catalog_total():
    view = year_view(2024, inputs(BASIC), as_of=CLOSED)

    domains = {d.slug: d for d in view.domains}
    assert domains["development"].share == pytest.approx(0.9)
    categories = {c.slug: c.share for c in domains["development"].categories}
    assert categories == pytest.approx({"web": 0.8, "testing": 0.1})


def test_catalog_share_is_measured_against_all_of_pypi():
    totals = {date(2024, 6, 1): 400}

    view = year_view(2024, inputs(BASIC, totals=totals), as_of=CLOSED)

    assert view.catalog_share == pytest.approx(0.25)
    assert view.volume.total == 400


def test_the_year_in_progress_compares_a_window_of_the_same_length():
    series = {"django": {date(2024, 1, 10): 5, date(2024, 12, 1): 7, date(2025, 1, 10): 9}}

    view = year_view(2025, inputs(series), as_of=date(2025, 1, 31))

    assert view.status == "ytd"
    assert (view.period_start, view.period_end) == (date(2025, 1, 1), date(2025, 1, 31))
    assert (view.previous_start, view.previous_end) == (date(2024, 1, 1), date(2024, 1, 31))
    assert (view.volume.total, view.volume.previous) == (9, 5)
    assert view.volume.growth == pytest.approx(0.8)


def test_a_comparison_across_a_discontinuity_has_no_growth():
    series = {"django": yearly({2017: 5, 2018: 10, 2019: 20, 2020: 40})}

    growth = {
        year: year_view(year, inputs(series), as_of=date(2020, 12, 31)).volume.growth
        for year in (2018, 2019, 2020)
    }

    assert growth[2018] is None
    assert growth[2019] is None
    assert growth[2020] == pytest.approx(1.0)


def test_discontinuities_of_the_period_are_reported():
    series = {"django": yearly({2017: 5, 2018: 10})}

    view = year_view(2018, inputs(series), as_of=date(2018, 12, 31))

    assert view.volume.discontinuities == (date(2018, 7, 27),)


def test_2017_has_no_previous_year_to_compare():
    view = year_view(2017, inputs({"django": yearly({2016: 3, 2017: 5})}), as_of=CLOSED)

    assert view.volume.previous is None
    assert view.volume.growth is None
    assert view.movers_up == () and view.movers_down == () and view.newcomers == ()


def test_the_coverage_of_the_year_comes_from_the_quality_calendar():
    view = year_view(2019, inputs({"django": yearly({2019: 1})}), as_of=CLOSED)

    assert (view.coverage.expected, view.coverage.gap) == (365, 2)


@pytest.mark.parametrize("year", [2016, 2025])
def test_years_outside_the_range_are_rejected(year):
    with pytest.raises(ValueError, match=str(year)):
        year_view(year, inputs(BASIC), as_of=CLOSED)


def test_a_year_without_data_is_rejected():
    with pytest.raises(ValueError, match="2022"):
        year_view(2022, inputs(BASIC), as_of=CLOSED)


def test_movers_are_ordered_by_change_in_share_points():
    view = year_view(2024, inputs(BASIC), as_of=CLOSED)

    # 2023: django 30/100, flask 10/100, pytest 10/100. 2024: 60/100, 20/100, 10/100.
    assert [(m.project, m.share_change) for m in view.movers_up] == [
        ("django", pytest.approx(30.0)),
        ("flask", pytest.approx(10.0)),
    ]
    assert view.movers_down == ()


def test_foundations_count_in_shares_but_are_not_movers():
    view = year_view(2024, inputs(BASIC), as_of=CLOSED)

    assert "six" not in {m.project for m in (*view.movers_up, *view.movers_down)}


def test_a_mover_reports_its_position_change_among_eligible_packages():
    series = {
        "django": yearly({2023: 30, 2024: 10}),
        "flask": yearly({2023: 10, 2024: 30}),
    }

    view = year_view(2024, inputs(series), as_of=CLOSED)

    [up] = view.movers_up
    [down] = view.movers_down
    assert (up.project, up.rank, up.rank_change) == ("flask", 1, 1)
    assert (down.project, down.rank, down.rank_change) == ("django", 2, -1)


def test_a_package_without_previous_downloads_has_no_position_change():
    series = {"django": yearly({2023: 10, 2024: 10}), "flask": yearly({2024: 10})}

    view = year_view(2024, inputs(series), as_of=CLOSED)

    assert [(m.project, m.rank_change) for m in view.movers_up] == [("flask", None)]


def test_at_most_ten_movers_per_direction():
    many = {f"p{i}": library(f"p{i}", "web") for i in range(30)}
    series = {p: yearly({2023: 100 + i, 2024: 200 - i * 3}) for i, p in enumerate(many)}
    data = YearInputs(
        series,
        {date(2024, 6, 1): 10**6, date(2023, 6, 1): 10**6},
        {},
        Catalog(many, DOMAINS, releases=RELEASES),
    )

    view = year_view(2024, data, as_of=CLOSED)

    assert len(view.movers_up) == 10
    assert len(view.movers_down) == 10


TOP = {2023: ("django", "six"), 2024: ("flask", "django", "six", "pytest")}


def test_newcomers_are_first_timers_in_the_top_in_ranking_order():
    view = year_view(2024, inputs(BASIC, top=TOP), as_of=CLOSED)

    assert [(n.project, n.rank) for n in view.newcomers] == [("flask", 1), ("pytest", 4)]


def test_foundations_are_not_newcomers():
    top = {2023: ("django",), 2024: ("six", "django")}

    assert year_view(2024, inputs(BASIC, top=top), as_of=CLOSED).newcomers == ()


def test_a_renamed_package_is_not_a_newcomer_if_its_old_name_was_in_the_top():
    series = {"oldname": yearly({2023: 5}), "newname": yearly({2024: 5})}
    top = {2023: ("oldname",), 2024: ("newname",)}

    assert year_view(2024, inputs(series, top=top), as_of=CLOSED).newcomers == ()


def test_renames_are_never_summed():
    series = {"oldname": yearly({2023: 5, 2024: 3}), "newname": yearly({2024: 7})}

    view = year_view(2024, inputs(series), as_of=CLOSED)

    movers = {m.project: m for m in (*view.movers_up, *view.movers_down)}
    assert movers["newname"].share == pytest.approx(0.7)
    assert movers["oldname"].share == pytest.approx(0.3)


def months_of(year: int, values: dict[str, int]) -> dict[date, dict[str, int]]:
    return {date(year, 1, 1): values}


def test_python_versions_exclude_unknown_and_junk_from_their_shares():
    python = months_of(2024, {"3.12": 75, "3.9": 25, "": 20, "3.51": 80})

    view = year_view(2024, inputs(BASIC, python=python), as_of=CLOSED)

    assert [(v.version, v.share) for v in view.python_versions] == [
        ("3.12", pytest.approx(0.75)),
        ("3.9", pytest.approx(0.25)),
    ]
    assert view.python_unknown_share == pytest.approx(0.1)
    assert view.python_other_share == pytest.approx(0.4)


def test_versions_are_listed_from_newest_to_oldest_numerically():
    python = months_of(2024, {"3.9": 1, "3.10": 1, "2.7": 1})

    view = year_view(2024, inputs(BASIC, python=python), as_of=CLOSED)

    assert [v.version for v in view.python_versions] == ["3.10", "3.9", "2.7"]


def test_only_closed_months_of_the_period_count_for_versions():
    python = {
        date(2024, 12, 1): {"3.12": 1},
        date(2025, 1, 1): {"3.12": 10},
        date(2025, 2, 1): {"3.12": 100},
    }
    series = {"django": {date(2024, 1, 2): 1, date(2025, 2, 10): 1}}

    view = year_view(2025, inputs(series, python=python), as_of=date(2025, 2, 10))

    assert view.python_versions[0].downloads == 10


def test_timeline_has_releases_and_end_of_life_of_the_year():
    series = {"django": yearly({2020: 1}), "flask": yearly({2021: 1})}

    view = year_view(2020, inputs(series), as_of=CLOSED)

    assert [(e.date, e.version, e.kind) for e in view.timeline] == [
        (date(2020, 1, 1), "2.7", "end_of_life"),
        (date(2020, 10, 5), "3.9", "release"),
    ]


def test_timeline_stops_at_as_of():
    view = year_view(
        2020,
        inputs({"django": {date(2020, 1, 2): 1}}),
        as_of=date(2020, 6, 30),
    )

    assert [e.version for e in view.timeline] == ["2.7"]


YEAR_DAYS = st.dates(date(2017, 1, 1), date(2021, 12, 31))
SERIES = st.dictionaries(YEAR_DAYS, st.integers(1, 10**9), min_size=1, max_size=40)
ALL_SERIES = st.fixed_dictionaries({p: SERIES for p in ("django", "flask", "pytest", "six")})


def eligible(series, year, as_of):
    assume(as_of.year >= year)
    start = date(year, 1, 1)
    assume(any(start <= d <= min(as_of, date(year, 12, 31)) for s in series.values() for d in s))


@given(ALL_SERIES, st.integers(2017, 2021), YEAR_DAYS)
def test_shares_add_up_to_one(series, year, as_of):
    eligible(series, year, as_of)

    view = year_view(year, inputs(series), as_of=as_of)

    assert sum(d.share for d in view.domains) == pytest.approx(1)
    for domain in view.domains:
        assert sum(c.share for c in domain.categories) == pytest.approx(domain.share)


@given(ALL_SERIES, st.integers(2018, 2021), YEAR_DAYS)
def test_the_compared_windows_have_the_same_length_while_in_progress(series, year, as_of):
    eligible(series, year, as_of)

    view = year_view(year, inputs(series), as_of=as_of)

    if view.status == "ytd":
        length = view.period_end - view.period_start
        assert view.previous_end - view.previous_start == length


@given(ALL_SERIES, st.integers(2017, 2021), YEAR_DAYS, st.integers(1, 400))
def test_later_days_do_not_change_a_view(series, year, as_of, days_later):
    eligible(series, year, as_of)
    later = {p: {**s, as_of + timedelta(days=days_later): 123} for p, s in series.items()}

    assert year_view(year, inputs(later), as_of=as_of) == year_view(
        year, inputs(series), as_of=as_of
    )


def test_a_closed_year_view_survives_a_json_round_trip():
    view = year_view(2024, inputs(BASIC, top=TOP), as_of=CLOSED)

    assert type(view).model_validate_json(view.model_dump_json()) == view


def test_a_year_ending_exactly_on_as_of_is_closed():
    assert year_view(2024, inputs(BASIC), as_of=CLOSED).status == "closed"


def test_the_first_year_has_no_newcomers_even_with_a_ranking():
    view = year_view(
        2017, inputs({"django": yearly({2017: 5})}, top={2017: ("django",)}), as_of=CLOSED
    )

    assert view.newcomers == ()


def test_the_2026_drop_blocks_growth_like_the_2018_jump():
    series = {"django": yearly({2025: 10, 2026: 30})}

    view = year_view(2026, inputs(series), as_of=date(2026, 11, 8))

    assert view.volume.growth is None
    assert view.volume.discontinuities == (date(2026, 8, 25),)
