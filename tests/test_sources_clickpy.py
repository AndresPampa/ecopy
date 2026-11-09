"""Contrato del adaptador de ClickPy, contra respuestas reales grabadas."""

import json
import re
from datetime import date, timedelta
from pathlib import Path

import httpx
import pytest

from ecopy.sources.clickpy import (
    ChecksumMismatch,
    ClickPy,
    SourceError,
    SourceUnavailable,
    TruncatedResult,
)

FIXTURES = Path(__file__).parent / "fixtures" / "clickpy"
TAG = re.compile(r"/\* ecopy:(\w+) \*/")
JANUARY = (date(2024, 1, 1), date(2024, 1, 31))


def replay(tamper=None) -> httpx.Client:
    """Cliente que responde cada consulta con la respuesta grabada para su etiqueta."""
    return httpx.Client(transport=httpx.MockTransport(recorded_handler(tamper)))


def recorded_handler(tamper=None, name: str = "fastapi_2024-01.json"):
    """Handler que reproduce lo grabado.

    `tamper(exchanges)` altera lo grabado para simular una respuesta defectuosa de ClickPy.
    """
    exchanges = json.loads((FIXTURES / name).read_text())
    if tamper:
        tamper(exchanges)

    def handler(request: httpx.Request) -> httpx.Response:
        tag = TAG.search(request.content.decode()).group(1)
        recorded = exchanges[tag]
        headers = {"X-ClickHouse-Summary": json.dumps(recorded["summary"])}
        return httpx.Response(200, headers=headers, text=recorded["body"])

    return handler


def test_daily_downloads_returns_one_verified_record_per_day():
    source = ClickPy(replay())

    batch = source.daily_downloads(["fastapi"], date(2024, 1, 1), date(2024, 1, 31))

    assert batch.source == "clickpy"
    assert [r.date for r in batch.rows] == [date(2024, 1, 1) + timedelta(days=i) for i in range(31)]
    assert {r.project for r in batch.rows} == {"fastapi"}
    assert sum(r.downloads for r in batch.rows) == 35_561_750


def test_partial_read_is_rejected_instead_of_returned():
    def partial_read(exchanges):
        exchanges["daily"]["summary"]["total_rows_to_read"] = "999999"

    with pytest.raises(TruncatedResult):
        ClickPy(replay(tamper=partial_read)).daily_downloads(["fastapi"], *JANUARY)


def test_result_at_the_row_limit_is_rejected():
    def thousand_rows(exchanges):
        line = exchanges["daily"]["body"].splitlines()[0]
        exchanges["daily"]["body"] = "\n".join([line] * 1000) + "\n"

    with pytest.raises(TruncatedResult):
        ClickPy(replay(tamper=thousand_rows)).daily_downloads(["fastapi"], *JANUARY)


def test_result_near_the_byte_limit_is_rejected():
    def huge_result(exchanges):
        exchanges["daily"]["summary"]["result_bytes"] = "9500000"

    with pytest.raises(TruncatedResult):
        ClickPy(replay(tamper=huge_result)).daily_downloads(["fastapi"], *JANUARY)


def test_download_that_does_not_match_server_totals_is_rejected():
    def altered_count(exchanges):
        exchanges["daily"]["body"] = exchanges["daily"]["body"].replace(":604527,", ":1,", 1)

    with pytest.raises(ChecksumMismatch):
        ClickPy(replay(tamper=altered_count)).daily_downloads(["fastapi"], *JANUARY)


def test_project_missing_from_the_download_is_rejected():
    def dropped_project(exchanges):
        exchanges["daily"]["body"] = ""

    with pytest.raises(ChecksumMismatch):
        ClickPy(replay(tamper=dropped_project)).daily_downloads(["fastapi"], *JANUARY)


def test_project_without_downloads_yields_no_records():
    def no_data(exchanges):
        exchanges["daily"]["body"] = exchanges["checksums"]["body"] = ""

    batch = ClickPy(replay(tamper=no_data)).daily_downloads(["fastapi"], *JANUARY)

    assert batch.rows == ()


def failing(handler_error, then=None):
    """Cliente que falla (status o excepción) y cuenta los intentos; `then` responde al resto."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if then is not None and len(calls) > 1:
            return then(request)
        if isinstance(handler_error, int):
            return httpx.Response(handler_error, text="error")
        raise handler_error

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


def no_sleep(_seconds: float) -> None:
    pass


def test_persistent_server_error_raises_unavailable_after_retrying():
    client, calls = failing(503)

    with pytest.raises(SourceUnavailable):
        ClickPy(client, sleep=no_sleep).daily_downloads(["fastapi"], *JANUARY)

    assert len(calls) == 3


def test_timeout_raises_unavailable():
    client, _ = failing(httpx.ReadTimeout("timeout"))

    with pytest.raises(SourceUnavailable):
        ClickPy(client, sleep=no_sleep).daily_downloads(["fastapi"], *JANUARY)


def test_transient_server_error_is_recovered_by_retrying():
    client, _ = failing(503, then=recorded_handler())

    batch = ClickPy(client, sleep=no_sleep).daily_downloads(["fastapi"], *JANUARY)

    assert len(batch.rows) == 31


def test_rejected_query_fails_immediately_without_retrying():
    client, calls = failing(400)

    with pytest.raises(SourceError) as error:
        ClickPy(client, sleep=no_sleep).daily_downloads(["fastapi"], *JANUARY)

    assert not isinstance(error.value, SourceUnavailable)
    assert len(calls) == 1


def test_large_project_lists_are_split_into_batches_within_the_limit():
    projects = [f"pkg-{i:03}" for i in range(120)]
    batch_sizes = []

    def handler(request: httpx.Request) -> httpx.Response:
        query = request.content.decode()
        names = sorted(set(re.findall(r"pkg-\d+", query)))
        if "ecopy:daily" in query:
            batch_sizes.append(len(names))
            body = "".join(f"{n}\t2024-01-01:10\n" for n in names)
        else:
            body = "".join(f"{n}\t1\t10\n" for n in names)
        summary = {"read_rows": "1", "total_rows_to_read": "1", "result_bytes": "10"}
        return httpx.Response(200, headers={"X-ClickHouse-Summary": json.dumps(summary)}, text=body)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    batch = ClickPy(client).daily_downloads(projects, *JANUARY)

    assert [r.project for r in batch.rows] == projects
    assert batch_sizes == [50, 50, 20]


def test_inverted_date_range_is_rejected():
    with pytest.raises(ValueError):
        ClickPy(replay()).daily_downloads(["fastapi"], JANUARY[1], JANUARY[0])
