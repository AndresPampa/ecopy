"""Ingesta: ventanas por paquete, reobservación, validación previa y registro de la corrida."""

from datetime import UTC, date, datetime, timedelta

import pytest

from ecopy.models import (
    DailyDownload,
    DailyTotal,
    DownloadBatch,
    PypiTotalsBatch,
    PythonMinorBatch,
    PythonMinorMonth,
    StarWeek,
)
from ecopy.pipeline import ingest, ingest_stars, python_cutoff, validate_store
from ecopy.sources.clickpy import SourceError, SourceUnavailable
from ecopy.sources.github import BudgetExhausted, RepoStars
from ecopy.store import Store

SOURCE_START = date(2016, 1, 22)
YESTERDAY = date(2024, 3, 9)
NOW = datetime(2024, 3, 10, 6, 0, tzinfo=UTC)
LEVEL = 1000


class FakeSource:
    """Fuente en memoria que respeta el rango pedido y registra lo que le piden."""

    def __init__(self, downloads, *, totals=None) -> None:
        self.downloads = downloads
        self.totals = totals
        self.calls: list[tuple] = []
        self.error: Exception | None = None

    def daily_downloads(self, projects, start, end):
        self.calls.append(("daily", tuple(projects), start, end))
        if self.error:
            raise self.error
        rows = sorted(
            (DailyDownload(p, d, n) for (p, d), n in self.downloads.items() if p in projects),
            key=lambda r: (r.project, r.date),
        )
        return DownloadBatch("clickpy", tuple(r for r in rows if start <= r.date <= end))

    def pypi_daily_totals(self, start, end):
        self.calls.append(("totals", start, end))
        days = self.totals or {
            start + timedelta(days=i): LEVEL for i in range((end - start).days + 1)
        }
        rows = tuple(DailyTotal(d, n) for d, n in sorted(days.items()) if start <= d <= end)
        return PypiTotalsBatch("clickpy", rows)

    def python_minor_monthly(self, before):
        self.calls.append(("python", before))
        return PythonMinorBatch("clickpy", self.python_rows(before))

    def python_rows(self, before):
        return ()

    def of(self, kind):
        return [call for call in self.calls if call[0] == kind]


def recent_days(project: str, *, until: date = YESTERDAY, days: int = 10, level: int = 5):
    return {(project, until - timedelta(days=i)): level for i in range(days)}


def run(source, store, *, projects=("fastapi",), now=NOW, **kwargs):
    return ingest(projects, source, store, now=now, **kwargs)


def later(hours: int) -> datetime:
    return NOW + timedelta(hours=hours)


def test_a_package_without_data_is_backfilled_from_the_start_of_the_source(tmp_path):
    source = FakeSource(recent_days("fastapi"))

    report = run(source, Store(tmp_path))

    assert report.status == "ok"
    assert source.of("daily") == [("daily", ("fastapi",), SOURCE_START, YESTERDAY)]
    assert Store(tmp_path).daily_downloads(["fastapi"])["fastapi"][YESTERDAY] == 5
    assert report.datasets["downloads_daily"].new_rows == 10


def test_the_last_seven_saved_days_are_reobserved(tmp_path):
    store = Store(tmp_path)
    source = FakeSource(recent_days("fastapi", until=YESTERDAY - timedelta(days=1)))
    run(source, store, now=NOW - timedelta(days=1))
    source = FakeSource(recent_days("fastapi"))

    run(source, store)

    last_saved = YESTERDAY - timedelta(days=1)
    assert source.of("daily") == [
        ("daily", ("fastapi",), last_saved - timedelta(days=6), YESTERDAY)
    ]


def test_a_correction_inside_the_window_is_written_and_counted(tmp_path):
    store = Store(tmp_path)
    run(FakeSource(recent_days("fastapi")), store)
    changed = {**recent_days("fastapi"), ("fastapi", YESTERDAY): 9}

    report = run(FakeSource(changed), store, now=later(24))

    assert report.datasets["downloads_daily"].revised_rows == 1
    assert store.daily_downloads(["fastapi"])["fastapi"][YESTERDAY] == 9


def test_reobserving_without_changes_writes_no_data(tmp_path):
    store = Store(tmp_path)
    run(FakeSource(recent_days("fastapi")), store)
    files = sorted(tmp_path.rglob("*.parquet"))

    report = run(FakeSource(recent_days("fastapi")), store, now=later(1))

    assert report.status == "ok"
    assert sorted(tmp_path.rglob("*.parquet")) == files


def test_no_reobservation_starts_the_day_after_the_last_saved(tmp_path):
    store = Store(tmp_path)
    data = recent_days("fastapi", until=YESTERDAY - timedelta(days=2))
    run(FakeSource(data), store, now=NOW - timedelta(days=2))
    source = FakeSource(recent_days("fastapi"))

    run(source, store, reobserve_days=0)

    assert source.of("daily")[0][2] == YESTERDAY - timedelta(days=1)


def test_a_dormant_package_does_not_drag_the_window_of_the_others(tmp_path):
    store = Store(tmp_path)
    dormant = {("old", date(2020, 1, 1)): 1}
    run(FakeSource({**recent_days("fastapi"), **dormant}), store, projects=("fastapi", "old"))
    source = FakeSource({**recent_days("fastapi"), **dormant})

    run(source, store, projects=("fastapi", "old"), now=later(24))

    assert source.of("daily")[0][2] == YESTERDAY - timedelta(days=6)


def test_an_outage_is_recovered_from_the_last_saved_day(tmp_path):
    store = Store(tmp_path)
    before_outage = YESTERDAY - timedelta(days=2)
    run(FakeSource(recent_days("fastapi", until=before_outage)), store, now=NOW - timedelta(days=2))
    source = FakeSource(recent_days("fastapi"))

    report = run(source, store)

    assert source.of("daily")[0][2:] == (before_outage - timedelta(days=6), YESTERDAY)
    assert report.datasets["downloads_daily"].new_rows == 2


def test_new_and_known_packages_go_to_their_own_window_in_one_run(tmp_path):
    store = Store(tmp_path)
    run(FakeSource(recent_days("fastapi")), store)
    source = FakeSource({**recent_days("fastapi"), **recent_days("django")})

    report = run(source, store, projects=("fastapi", "django"), now=later(1))

    assert report.status == "ok"
    assert sorted(source.of("daily"), key=lambda call: call[2]) == [
        ("daily", ("django",), SOURCE_START, YESTERDAY),
        ("daily", ("fastapi",), YESTERDAY - timedelta(days=6), YESTERDAY),
    ]


def test_an_invalid_candidate_writes_no_data_and_records_the_failure(tmp_path):
    store = Store(tmp_path)
    totals = {YESTERDAY - timedelta(days=i): LEVEL for i in range(1, 40)}
    source = FakeSource(recent_days("fastapi", level=1), totals={**totals, YESTERDAY: 1})

    report = run(source, store)

    assert report.status == "failed"
    assert [p.code for p in report.problems] == ["volume"]
    assert not list(tmp_path.rglob("*.parquet"))
    assert [r.status for r in store.runs()] == ["failed"]


def test_a_source_error_records_the_failure(tmp_path):
    store = Store(tmp_path)
    source = FakeSource({})
    source.error = SourceUnavailable("no responde")

    report = run(source, store)

    assert report.status == "failed"
    assert report.problems[0].code == "source_error"
    assert "no responde" in report.problems[0].detail
    assert not list(tmp_path.rglob("*.parquet"))


def test_an_unexpected_error_records_the_failure_and_is_raised(tmp_path):
    store = Store(tmp_path)
    source = FakeSource({})
    source.error = KeyError("X-ClickHouse-Summary")

    with pytest.raises(KeyError):
        run(source, store)

    [failed] = store.runs()
    assert failed.status == "failed"
    assert failed.problems[0].code == "internal_error"
    assert "X-ClickHouse-Summary" in failed.problems[0].detail
    assert not list(tmp_path.rglob("*.parquet"))


def test_totals_use_their_own_window(tmp_path):
    store = Store(tmp_path)
    source = FakeSource(recent_days("fastapi"))
    run(source, store)
    assert source.of("totals") == [("totals", SOURCE_START, YESTERDAY)]
    source = FakeSource(recent_days("fastapi"))

    run(source, store, now=later(1))

    assert source.of("totals") == [("totals", YESTERDAY - timedelta(days=6), YESTERDAY)]


@pytest.mark.parametrize(
    ("end", "cutoff"),
    [
        (date(2024, 1, 31), date(2024, 2, 1)),
        (date(2024, 2, 10), date(2024, 2, 1)),
        (date(2023, 12, 31), date(2024, 1, 1)),
    ],
)
def test_python_cutoff_is_the_first_month_not_closed(end, cutoff):
    assert python_cutoff(end) == cutoff


class WithVersions(FakeSource):
    def python_rows(self, before):
        month = date(before.year, before.month - 1, 1) if before.month > 1 else None
        total = LEVEL * ((before - month).days) if month else 0
        return (PythonMinorMonth(month, "3.12", total),) if month else ()


def test_python_versions_are_fetched_only_when_a_closed_month_is_missing(tmp_path):
    store = Store(tmp_path)
    source = WithVersions(recent_days("fastapi"))
    run(source, store)
    assert source.of("python") == [("python", date(2024, 3, 1))]
    assert store.python_minor_monthly() == {date(2024, 2, 1): {"3.12": 29_000}}

    again = WithVersions(recent_days("fastapi"))
    run(again, store, now=later(24))

    assert again.of("python") == []


def test_each_run_is_recorded_in_order_with_its_counts(tmp_path):
    store = Store(tmp_path)
    run(FakeSource(recent_days("fastapi")), store)
    run(FakeSource(recent_days("fastapi")), store, now=later(1))

    runs = store.runs()

    assert [r.id for r in runs] == ["20240310T060000Z", "20240310T070000Z"]
    assert runs[0].last_day == YESTERDAY
    assert runs[0].datasets["pypi_total_daily"].new_rows > 0


def test_validating_a_healthy_store_finds_no_problems(tmp_path):
    store = Store(tmp_path)
    run(FakeSource(recent_days("fastapi")), store)

    assert validate_store(("fastapi",), store, now=later(24)) == []


def test_validating_a_stale_store_reports_it(tmp_path):
    store = Store(tmp_path)
    run(FakeSource(recent_days("fastapi")), store)

    problems = validate_store(("fastapi",), store, now=NOW + timedelta(days=10))

    assert [p.code for p in problems] == ["stale"]


class FakeGitHub:
    """Responde con semanas fijas y se queda sin consultas después de `limit` repos."""

    def __init__(self, limit=None, failing=(), moved=None):
        self.limit = limit
        self.failing = set(failing)
        self.moved = moved or {}
        self.calls = []
        self.attempts = 0
        self.requests = 0

    def _answer(self, repo, kind):
        self.attempts += 1
        if self.limit is not None and len(self.calls) >= self.limit:
            raise BudgetExhausted("budget")
        self.calls.append((repo, kind))
        self.requests += 2
        if repo in self.failing:
            raise SourceError(f"{repo}: 404")
        weeks = (StarWeek(repo, date(2024, 1, 7), 10),)
        return RepoStars(repo, self.moved.get(repo, repo), 10, weeks)

    def full_history(self, repo):
        return self._answer(repo, "full")

    def recent(self, repo):
        return self._answer(repo, "recent")


STARS_NOW = datetime(2024, 2, 1, tzinfo=UTC)


def test_new_repos_get_a_backfill_and_known_repos_an_update(tmp_path):
    store = Store(tmp_path)
    ingest_stars(["a/b"], FakeGitHub(), store, now=STARS_NOW)
    source = FakeGitHub()

    report = ingest_stars(["a/b", "c/d"], source, store, now=STARS_NOW + timedelta(days=1))

    assert source.calls == [("c/d", "full"), ("a/b", "recent")]
    assert report.backfilled == ("c/d",) and report.updated == ("a/b",)
    assert store.star_totals(["a/b"])["a/b"] == {date(2024, 2, 1): 10, date(2024, 2, 2): 10}


def test_running_out_of_requests_saves_what_finished_and_resumes_later(tmp_path):
    store = Store(tmp_path)

    first = ingest_stars(["a/b", "c/d", "e/f"], FakeGitHub(limit=1), store, now=STARS_NOW)

    assert (first.status, first.pending, first.stopped) == ("partial", 2, "budget")
    assert store.backfilled_repos() == {"a/b"}

    source = FakeGitHub()
    ingest_stars(["a/b", "c/d", "e/f"], source, store, now=STARS_NOW + timedelta(hours=1))
    assert source.calls[:2] == [("c/d", "full"), ("e/f", "full")]


def test_a_run_stops_trying_as_soon_as_it_runs_out_of_requests(tmp_path):
    source = FakeGitHub(limit=1)

    ingest_stars(["a/b", "c/d", "e/f"], source, Store(tmp_path), now=STARS_NOW)

    assert source.attempts == 2


def test_a_failing_repo_is_reported_and_does_not_stop_the_run(tmp_path):
    store = Store(tmp_path)

    report = ingest_stars(["a/b", "c/d"], FakeGitHub(failing=["a/b"]), store, now=STARS_NOW)

    assert report.failed == (("a/b", "a/b: 404"),)
    assert report.backfilled == ("c/d",)
    assert report.status == "partial"


def test_a_moved_repo_is_reported_and_keeps_its_declared_name(tmp_path):
    store = Store(tmp_path)

    report = ingest_stars(["a/b"], FakeGitHub(moved={"a/b": "x/y"}), store, now=STARS_NOW)

    assert report.moved == (("a/b", "x/y"),)
    assert set(store.star_weeks(["a/b"])) == {"a/b"}


def test_an_interrupted_run_keeps_the_repos_it_finished(tmp_path):
    store = Store(tmp_path)
    source = FakeGitHub()
    original = source.full_history

    def interrupted(repo):
        if repo == "c/d":
            raise KeyboardInterrupt
        return original(repo)

    source.full_history = interrupted

    with pytest.raises(KeyboardInterrupt):
        ingest_stars(["a/b", "c/d"], source, store, now=STARS_NOW)

    assert store.backfilled_repos() == {"a/b"}


def test_a_complete_run_says_so(tmp_path):
    report = ingest_stars(["a/b"], FakeGitHub(), Store(tmp_path), now=STARS_NOW)

    assert (report.status, report.pending, report.stopped, report.requests) == (
        "complete",
        0,
        None,
        2,
    )
