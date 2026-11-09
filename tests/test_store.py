"""Store append-only sobre un directorio real: lo escrito se lee y nunca se reescribe."""

from datetime import UTC, date, datetime, timedelta

import pyarrow.parquet as pq
import pytest

from ecopy.models import (
    DailyDownload,
    DailyTotal,
    DownloadBatch,
    PypiTotalsBatch,
    PythonMinorBatch,
    PythonMinorMonth,
    Run,
    YearView,
)
from ecopy.store import ImmutabilityError, Store

RUN = Run(
    id="20240201T000000Z-backfill",
    captured_at=datetime(2024, 2, 1, tzinfo=UTC),
    acquisition="backfill",
)


def batch(*rows: tuple[str, date, int]) -> DownloadBatch:
    return DownloadBatch("clickpy", tuple(DailyDownload(*row) for row in rows))


def test_appended_downloads_are_read_back_ordered_by_date(tmp_path):
    store = Store(tmp_path)

    store.append(
        batch(("fastapi", date(2024, 1, 2), 20), ("fastapi", date(2024, 1, 1), 10)),
        RUN,
    )

    series = store.daily_downloads(["fastapi"])
    assert list(series["fastapi"].items()) == [(date(2024, 1, 1), 10), (date(2024, 1, 2), 20)]


def test_a_run_writes_one_file_per_year_it_touches(tmp_path):
    paths = (
        Store(tmp_path)
        .append(
            batch(("fastapi", date(2023, 12, 31), 1), ("fastapi", date(2024, 1, 1), 2)),
            RUN,
        )
        .paths
    )

    assert sorted(p.relative_to(tmp_path).as_posix() for p in paths) == [
        f"raw/clickpy/downloads_daily/year=2023/{RUN.id}.parquet",
        f"raw/clickpy/downloads_daily/year=2024/{RUN.id}.parquet",
    ]


def test_every_written_row_carries_its_provenance(tmp_path):
    [path] = Store(tmp_path).append(batch(("fastapi", date(2024, 1, 1), 10)), RUN).paths

    row = pq.read_table(path).to_pylist()[0]

    assert row["source"] == "clickpy"
    assert row["acquisition"] == "backfill"
    assert row["captured_at"] == RUN.captured_at
    assert row["ingestion_run_id"] == RUN.id


def run_captured(id: str, days_later: int) -> Run:
    return Run(id, RUN.captured_at + timedelta(days=days_later), "observed")


def snapshot(root) -> dict:
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_repeating_a_run_id_fails_and_changes_nothing(tmp_path):
    store = Store(tmp_path)
    store.append(batch(("fastapi", date(2024, 1, 1), 10)), RUN)
    before = snapshot(tmp_path)

    with pytest.raises(ImmutabilityError):
        store.append(batch(("fastapi", date(2024, 1, 1), 999)), RUN)

    assert snapshot(tmp_path) == before


def test_a_rejected_run_leaves_no_partial_files_in_other_years(tmp_path):
    store = Store(tmp_path)
    store.append(batch(("fastapi", date(2024, 1, 1), 10)), RUN)
    before = snapshot(tmp_path)

    with pytest.raises(ImmutabilityError):
        store.append(
            batch(("fastapi", date(2023, 12, 31), 1), ("fastapi", date(2024, 1, 2), 2)),
            RUN,
        )

    assert snapshot(tmp_path) == before


def test_a_new_run_does_not_touch_previous_files(tmp_path):
    store = Store(tmp_path)
    store.append(batch(("fastapi", date(2024, 1, 1), 10)), RUN)
    before = snapshot(tmp_path)

    store.append(batch(("fastapi", date(2024, 1, 2), 20)), run_captured("later", 1))

    after = snapshot(tmp_path)
    assert {path: after[path] for path in before} == before
    assert len(after) == len(before) + 1


def test_a_later_capture_corrects_the_value_on_read(tmp_path):
    store = Store(tmp_path)
    store.append(batch(("fastapi", date(2024, 1, 1), 10)), RUN)

    store.append(batch(("fastapi", date(2024, 1, 1), 15)), run_captured("correction", 1))

    assert store.daily_downloads(["fastapi"])["fastapi"] == {date(2024, 1, 1): 15}


def test_write_order_does_not_decide_a_correction(tmp_path):
    store = Store(tmp_path)
    store.append(batch(("fastapi", date(2024, 1, 1), 15)), run_captured("newer", 5))

    store.append(batch(("fastapi", date(2024, 1, 1), 10)), run_captured("older", 1))

    assert store.daily_downloads(["fastapi"])["fastapi"] == {date(2024, 1, 1): 15}


def test_only_requested_projects_are_returned(tmp_path):
    store = Store(tmp_path)
    store.append(batch(("fastapi", date(2024, 1, 1), 1), ("numpy", date(2024, 1, 1), 2)), RUN)

    assert set(store.daily_downloads(["numpy", "absent"])) == {"numpy"}


def test_an_empty_store_has_no_series(tmp_path):
    assert Store(tmp_path).daily_downloads(["fastapi"]) == {}


def test_an_empty_batch_writes_nothing(tmp_path):
    assert Store(tmp_path).append(batch(), RUN).paths == []
    assert snapshot(tmp_path) == {}


def test_append_leaves_only_the_final_files(tmp_path):
    paths = Store(tmp_path).append(batch(("fastapi", date(2024, 1, 1), 10)), RUN).paths

    assert set(snapshot(tmp_path)) == set(paths)


@pytest.mark.parametrize("bad_id", ["", "../escape", "a/b", ".hidden"])
def test_a_run_id_must_be_safe_as_a_file_name(bad_id):
    with pytest.raises(ValueError):
        Run(bad_id, RUN.captured_at, "backfill")


def test_a_run_needs_a_timezone_aware_capture_time():
    with pytest.raises(ValueError):
        Run("naive", datetime(2024, 2, 1), "backfill")


def run_at(name: str, day: int) -> Run:
    return Run(id=name, captured_at=datetime(2024, 3, day, tzinfo=UTC), acquisition="observed")


def test_reobserving_identical_rows_writes_nothing(tmp_path):
    store = Store(tmp_path)
    store.append(batch(("fastapi", date(2024, 1, 1), 10)), RUN)
    before = snapshot(tmp_path)

    result = store.append(batch(("fastapi", date(2024, 1, 1), 10)), run_at("same", 1))

    assert (result.paths, result.new_rows, result.revised_rows) == ([], 0, 0)
    assert snapshot(tmp_path) == before


def test_only_new_or_changed_rows_are_written_and_counted(tmp_path):
    store = Store(tmp_path)
    store.append(
        batch(("fastapi", date(2024, 1, 1), 10), ("fastapi", date(2024, 1, 2), 20)),
        RUN,
    )

    result = store.append(
        batch(
            ("fastapi", date(2024, 1, 1), 10),
            ("fastapi", date(2024, 1, 2), 25),
            ("fastapi", date(2024, 1, 3), 30),
        ),
        run_at("reobserved", 1),
    )

    assert (result.new_rows, result.revised_rows) == (1, 1)
    [path] = result.paths
    assert [row["date"] for row in pq.read_table(path).to_pylist()] == [
        date(2024, 1, 2),
        date(2024, 1, 3),
    ]
    assert store.daily_downloads(["fastapi"])["fastapi"] == {
        date(2024, 1, 1): 10,
        date(2024, 1, 2): 25,
        date(2024, 1, 3): 30,
    }


def test_a_repeated_run_id_fails_even_with_nothing_to_write(tmp_path):
    store = Store(tmp_path)
    store.append(batch(("fastapi", date(2024, 1, 1), 10)), RUN)

    with pytest.raises(ImmutabilityError):
        store.append(batch(("fastapi", date(2024, 1, 1), 10)), RUN)


def totals(*rows: tuple[date, int]) -> PypiTotalsBatch:
    return PypiTotalsBatch("clickpy", tuple(DailyTotal(*row) for row in rows))


def versions(*rows: tuple[date, str, int]) -> PythonMinorBatch:
    return PythonMinorBatch("clickpy", tuple(PythonMinorMonth(*row) for row in rows))


def test_pypi_totals_are_their_own_dataset(tmp_path):
    store = Store(tmp_path)
    store.append(batch(("fastapi", date(2024, 1, 1), 10)), RUN)

    store.append(totals((date(2024, 1, 2), 200), (date(2024, 1, 1), 100)), RUN)

    assert list(store.pypi_daily_totals().items()) == [
        (date(2024, 1, 1), 100),
        (date(2024, 1, 2), 200),
    ]
    assert store.daily_downloads(["fastapi"])["fastapi"] == {date(2024, 1, 1): 10}


def test_python_versions_keep_raw_values_and_resolve_corrections(tmp_path):
    store = Store(tmp_path)
    month = date(2024, 1, 1)
    store.append(versions((month, "3.12", 5), (month, "", 1), (month, "\x1b[32m3.13", 2)), RUN)

    result = store.append(versions((month, "3.12", 7), (month, "", 1)), run_at("later", 1))

    assert (result.new_rows, result.revised_rows) == (0, 1)
    assert store.python_minor_monthly() == {month: {"3.12": 7, "": 1, "\x1b[32m3.13": 2}}


def test_empty_datasets_read_as_empty(tmp_path):
    store = Store(tmp_path)

    assert store.pypi_daily_totals() == {}
    assert store.python_minor_monthly() == {}
    assert store.last_days() == {}


def test_last_days_gives_the_newest_day_of_each_package(tmp_path):
    store = Store(tmp_path)
    store.append(
        batch(
            ("fastapi", date(2023, 12, 31), 1),
            ("fastapi", date(2024, 1, 5), 2),
            ("django", date(2024, 1, 3), 3),
        ),
        RUN,
    )

    assert store.last_days() == {"fastapi": date(2024, 1, 5), "django": date(2024, 1, 3)}


def frozen(year: int = 2024, methodology: int = 1, total: int = 100) -> YearView:
    return YearView(
        year=year,
        status="closed",
        methodology_version=methodology,
        period_start=date(year, 1, 1),
        period_end=date(year, 12, 31),
        previous_start=None,
        previous_end=None,
        coverage={"expected": 366, "gap": 0, "degraded": 0},
        volume={"total": total, "previous": None, "growth": None, "discontinuities": ()},
        catalog_share=0.5,
        domains=(),
        movers_up=(),
        movers_down=(),
        newcomers=(),
        python_versions=(),
        python_unknown_share=0.0,
        python_other_share=0.0,
        timeline=(),
    )


def test_a_year_without_freezing_is_none(tmp_path):
    assert Store(tmp_path).frozen_year(2024) is None


def test_a_frozen_year_is_read_back_identically(tmp_path):
    store = Store(tmp_path)

    path = store.freeze_year(frozen())

    assert store.frozen_year(2024) == frozen()
    assert path.relative_to(tmp_path).as_posix() == "frozen/year=2024/methodology=1.json"


def test_freezing_the_same_methodology_twice_fails_and_changes_nothing(tmp_path):
    store = Store(tmp_path)
    store.freeze_year(frozen())
    before = snapshot(tmp_path)

    with pytest.raises(ImmutabilityError):
        store.freeze_year(frozen(total=999))

    assert snapshot(tmp_path) == before


def test_the_highest_methodology_wins_and_the_old_file_stays(tmp_path):
    store = Store(tmp_path)
    store.freeze_year(frozen(total=1))
    store.freeze_year(frozen(methodology=2, total=2))
    store.freeze_year(frozen(methodology=10, total=10))

    assert store.frozen_year(2024).volume.total == 10
    assert len(list(tmp_path.rglob("*.json"))) == 3
