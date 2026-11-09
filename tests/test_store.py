"""Store append-only sobre un directorio real: lo escrito se lee y nunca se reescribe."""

from datetime import UTC, date, datetime, timedelta

import pyarrow.parquet as pq
import pytest

from ecopy.models import DailyDownload, DownloadBatch, Run
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
    paths = Store(tmp_path).append(
        batch(("fastapi", date(2023, 12, 31), 1), ("fastapi", date(2024, 1, 1), 2)),
        RUN,
    )

    assert sorted(p.relative_to(tmp_path).as_posix() for p in paths) == [
        f"raw/clickpy/downloads_daily/year=2023/{RUN.id}.parquet",
        f"raw/clickpy/downloads_daily/year=2024/{RUN.id}.parquet",
    ]


def test_every_written_row_carries_its_provenance(tmp_path):
    [path] = Store(tmp_path).append(batch(("fastapi", date(2024, 1, 1), 10)), RUN)

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
    assert Store(tmp_path).append(batch(), RUN) == []
    assert snapshot(tmp_path) == {}


def test_append_leaves_only_the_final_files(tmp_path):
    paths = Store(tmp_path).append(batch(("fastapi", date(2024, 1, 1), 10)), RUN)

    assert set(snapshot(tmp_path)) == set(paths)


@pytest.mark.parametrize("bad_id", ["", "../escape", "a/b", ".hidden"])
def test_a_run_id_must_be_safe_as_a_file_name(bad_id):
    with pytest.raises(ValueError):
        Run(bad_id, RUN.captured_at, "backfill")


def test_a_run_needs_a_timezone_aware_capture_time():
    with pytest.raises(ValueError):
        Run("naive", datetime(2024, 2, 1), "backfill")
