"""Vistas de navegación: cuota mensual, listados, dominios, categorías y releases."""

from datetime import date

from ecopy.catalog import Catalog, Domain, Library, PythonRelease
from ecopy.metrics import library_rows, library_view, releases_view, stars_view, taxonomy_view
from ecopy.models import CategoryShare, Coverage, DomainShare, VolumeView, YearView


def catalog() -> Catalog:
    libraries = {
        "fastapi": Library("fastapi", "web", ("async",), "fastapi/fastapi", None),
        "flask": Library("flask", "web", (), None, None),
        "pytest": Library("pytest", "testing", (), "pytest-dev/pytest", None),
        "old": Library("old", "testing", (), None, None),
        "new": Library("new", "testing", (), None, "old"),
    }
    domain_of = {"web": "development", "testing": "development"}
    return Catalog(libraries, domain_of, domains=(Domain("development", ("web", "testing")),))


def months(*pairs, year=2024) -> dict[date, int]:
    return {date(year, month, 1): value for month, value in pairs}


TOTALS = {date(2024, m, 1): 1000 for m in range(1, 13)}
AS_OF = date(2024, 3, 15)


def test_each_month_carries_its_share_of_all_pypi():
    view = library_view(
        "fastapi", months((1, 100), (2, 50)), as_of=date(2024, 2, 29), totals=TOTALS
    )

    assert [m.share for m in view.monthly] == [0.1, 0.05]


def test_without_totals_or_for_a_month_without_data_the_share_is_empty():
    series = months((1, 100), (3, 50))

    assert library_view("a", series, as_of=AS_OF).monthly[0].share is None
    assert library_view("a", series, as_of=AS_OF, totals=TOTALS).monthly[1].share is None


def test_the_view_takes_its_place_in_the_catalog():
    view = library_view("fastapi", months((1, 1)), as_of=AS_OF, catalog=catalog())

    assert (view.category, view.domain, view.tags) == ("web", "development", ("async",))
    assert view.repo == "fastapi/fastapi"


def test_a_rename_is_visible_from_both_names():
    old = library_view("old", months((1, 1)), as_of=AS_OF, catalog=catalog())
    new = library_view("new", months((1, 1)), as_of=AS_OF, catalog=catalog())

    assert (old.renamed_to, new.renamed_from) == ("new", "old")


def rows():
    views = [
        library_view(
            project, months((1, value), (2, value)), as_of=AS_OF, totals=TOTALS, catalog=catalog()
        )
        for project, value in (("flask", 10), ("fastapi", 30), ("pytest", 20))
    ]
    return library_rows(views)


def test_rows_go_from_most_to_least_downloaded_in_the_last_closed_month():
    found = rows()

    assert [r.project for r in found] == ["fastapi", "pytest", "flask"]
    assert found[0].downloads == 30 and found[0].month == date(2024, 2, 1)


def test_the_trend_uses_only_closed_months_and_at_most_thirty_six():
    series = {date(y, m, 1): 10 for y in (2021, 2022, 2023, 2024) for m in range(1, 13)}
    series = {d: v for d, v in series.items() if d <= AS_OF}
    series[date(2024, 3, 1)] = 99  # el mes en curso no debe entrar en la tendencia
    totals = {d: 100 for d in series}

    view = library_view("fastapi", series, as_of=AS_OF, totals=totals, catalog=catalog())

    assert library_rows([view])[0].trend == tuple([0.1] * 36)


def year(number, web, testing, status="closed") -> YearView:
    return YearView(
        year=number,
        status=status,
        methodology_version=1,
        period_start=date(number, 1, 1),
        period_end=date(number, 12, 31),
        previous_start=None,
        previous_end=None,
        coverage=Coverage(expected=365, gap=0, degraded=0),
        volume=VolumeView(total=1, previous=None, growth=None, discontinuities=()),
        catalog_share=0.5,
        domains=(
            DomainShare(
                slug="development",
                downloads=100,
                share=web + testing,
                categories=(
                    CategoryShare(slug="web", downloads=75, share=web),
                    CategoryShare(slug="testing", downloads=25, share=testing),
                ),
            ),
        ),
        movers_up=(),
        movers_down=(),
        newcomers=(),
        python_versions=(),
        python_unknown_share=0.0,
        python_other_share=0.0,
        timeline=(),
    )


def test_each_domain_and_category_has_its_share_per_year_and_its_libraries():
    years = (year(2023, 0.5, 0.25), year(2024, 0.25, 0.5, status="ytd"))

    domain = taxonomy_view(years, rows(), catalog())[0]

    assert [(s.year, s.share, s.status) for s in domain.shares] == [
        (2023, 0.75, "closed"),
        (2024, 0.75, "ytd"),
    ]
    web, testing = domain.categories
    assert [s.share for s in web.shares] == [0.5, 0.25]
    assert [r.project for r in web.rows] == ["fastapi", "flask"]
    assert [r.project for r in testing.rows] == ["pytest"]


def test_a_category_absent_from_a_year_has_no_point_that_year():
    years = (year(2023, 0.5, 0.25),)
    tree = Catalog({}, {"x": "development"}, domains=(Domain("development", ("x",)),))

    assert taxonomy_view(years, (), tree)[0].categories[0].shares == ()


def test_releases_go_from_newest_to_oldest_with_their_support_status():
    releases = (
        PythonRelease("2.5", date(2006, 9, 19), None),
        PythonRelease("3.8", date(2019, 10, 14), date(2024, 10, 7)),
        PythonRelease("3.13", date(2024, 10, 7), date(2029, 10, 31)),
    )

    view = releases_view(releases, as_of=date(2026, 11, 8))

    assert [(r.version, r.status) for r in view.releases] == [
        ("3.13", "supported"),
        ("3.8", "end_of_life"),
        ("2.5", "unknown"),
    ]
    assert view.as_of == date(2026, 11, 8)


def test_stars_accumulate_by_week_and_know_who_shares_the_repo():
    weeks = {date(2024, 1, 7): 10, date(2024, 1, 14): 0, date(2024, 1, 21): 5}
    counts = {date(2024, 1, 20): 14, date(2024, 1, 22): 17}

    view = stars_view("a/b", weeks, counts, shared_with=("x", "y"))

    assert [(p.week, p.stars) for p in view.points] == [
        (date(2024, 1, 7), 10),
        (date(2024, 1, 14), 10),
        (date(2024, 1, 21), 15),
    ]
    assert view.total == 17
    assert view.shared_with == ("x", "y")


def test_without_a_daily_count_the_total_is_the_accumulated_sum():
    assert stars_view("a/b", {date(2024, 1, 7): 10}, {}, shared_with=()).total == 10
