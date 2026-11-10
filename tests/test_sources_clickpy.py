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


SUMMARY = {"read_rows": "10", "total_rows_to_read": "10", "result_bytes": "100"}


def answering(bodies, *, summary=SUMMARY) -> httpx.Client:
    """Responde por etiqueta. Un valor puede ser una función que recibe el SQL."""

    def handler(request: httpx.Request) -> httpx.Response:
        sql = request.content.decode()
        body = bodies[TAG.search(sql).group(1)]
        text = body(sql) if callable(body) else body
        return httpx.Response(200, headers={"X-ClickHouse-Summary": json.dumps(summary)}, text=text)

    return httpx.Client(transport=httpx.MockTransport(handler))


TOTALS = {
    "totals": "2024-01-01:100,2024-01-02:250\n",
    "totals_checksums": "2\t350\n",
}


def test_pypi_daily_totals_returns_one_verified_record_per_day():
    batch = ClickPy(answering(TOTALS)).pypi_daily_totals(*JANUARY)

    assert batch.source == "clickpy"
    assert [(r.date, r.downloads) for r in batch.rows] == [
        (date(2024, 1, 1), 100),
        (date(2024, 1, 2), 250),
    ]


def test_pypi_daily_totals_that_do_not_match_are_rejected():
    with pytest.raises(ChecksumMismatch):
        ClickPy(answering({**TOTALS, "totals_checksums": "2\t351\n"})).pypi_daily_totals(*JANUARY)


def test_a_range_without_totals_yields_no_records():
    empty = {"totals": "\n", "totals_checksums": "0\t0\n"}

    assert ClickPy(answering(empty)).pypi_daily_totals(*JANUARY).rows == ()


def test_pypi_daily_totals_reject_an_inverted_range():
    with pytest.raises(ValueError, match="rango invertido"):
        ClickPy(answering(TOTALS)).pypi_daily_totals(date(2024, 2, 1), date(2024, 1, 1))


US = "\x1f"
RS = "\x1e"
# Valores reales de `python_minor`: vacío, escapes de terminal, comas, barras y espacios.
JUNK = "(main, Mar 11 2026, 17:42:35) [MSC v.1942 64 bit (AMD64)]"


def by_range(values):
    """Responde según el rango de `project` de la consulta."""

    def answer(sql: str) -> str:
        for marker, body in values.items():
            if f"project >= '{marker}'" in sql:
                return body
        raise AssertionError(f"rango inesperado: {sql}")

    return answer


def python_bodies(**overrides):
    packed = {
        "": f"2024-01-01{US}3.12{US}5{RS}2024-01-01{US}{US}1\n",
        "d": f"2024-01-01{US}3.12{US}2\n",
        "m": f"2024-01-01{US}\x1b[32m3.13{US}4{RS}2024-02-01{US}{JUNK}{US}3\n",
        "s": "\n",
    }
    checksums = {"": "6\n", "d": "2\n", "m": "7\n", "s": "0\n"}
    return {"python": by_range(packed), "python_checksums": by_range(checksums), **overrides}


def test_python_versions_are_added_across_project_ranges_keeping_raw_values():
    batch = ClickPy(answering(python_bodies())).python_minor_monthly(before=date(2024, 3, 1))

    assert {(r.month, r.python_minor): r.downloads for r in batch.rows} == {
        (date(2024, 1, 1), "3.12"): 7,
        (date(2024, 1, 1), ""): 1,
        (date(2024, 1, 1), "\x1b[32m3.13"): 4,
        (date(2024, 2, 1), JUNK): 3,
    }


def test_python_versions_that_do_not_match_a_range_are_rejected():
    wrong = python_bodies(
        python_checksums=by_range({"": "6\n", "d": "2\n", "m": "8\n", "s": "0\n"})
    )

    with pytest.raises(ChecksumMismatch):
        ClickPy(answering(wrong)).python_minor_monthly(before=date(2024, 3, 1))


def test_python_versions_reject_a_partial_read_of_the_big_table():
    partial = {**SUMMARY, "total_rows_to_read": "11"}

    with pytest.raises(TruncatedResult):
        ClickPy(answering(python_bodies(), summary=partial)).python_minor_monthly(
            before=date(2024, 3, 1)
        )


def test_python_versions_need_the_first_day_of_a_month():
    with pytest.raises(ValueError, match="primer día"):
        ClickPy(answering(python_bodies())).python_minor_monthly(before=date(2024, 3, 15))


def test_top_projects_are_grouped_by_year_in_ranking_order():
    body = "2017\trequests\t9\n2017\tsix\t5\n2018\tpip\t8\n2018\tsix\t7\n"

    top = ClickPy(answering({"top": body})).top_projects([2017, 2018], n=2)

    assert top == {2017: ("requests", "six"), 2018: ("pip", "six")}


def test_top_projects_are_read_a_few_years_per_query():
    seen = []

    def answer(sql: str) -> str:
        seen.append(sql)
        years = [int(y) for y in re.findall(r"toYear\(date\) IN \(([\d, ]+)\)", sql)[0].split(", ")]
        return "".join(f"{y}\tp{i}\t1\n" for y in years for i in range(2))

    top = ClickPy(answering({"top": answer})).top_projects(list(range(2017, 2024)), n=2)

    assert len(seen) == 2
    assert sorted(top) == list(range(2017, 2024))


def test_a_year_short_of_projects_is_rejected():
    with pytest.raises(ChecksumMismatch):
        ClickPy(answering({"top": "2017\trequests\t9\n"})).top_projects([2017], n=2)


def test_known_projects_are_the_ones_the_source_has():
    known = ClickPy(answering({"known": "fastapi\ndjango\n"})).known_projects(
        ["fastapi", "django", "tkinter"]
    )

    assert known == {"fastapi", "django"}


@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda s: s.daily_downloads(["fastapi"], *JANUARY), id="daily"),
        pytest.param(lambda s: s.known_projects(["fastapi"]), id="known"),
    ],
)
def test_a_response_without_its_summary_is_a_source_error(call):
    def no_summary(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="fastapi\t2024-01-01:1\n")

    client = httpx.Client(transport=httpx.MockTransport(no_summary))

    with pytest.raises(SourceError):
        call(ClickPy(client))


DAILY_OK = {"daily": "fastapi\t2024-01-01:1\n", "checksums": "fastapi\t1\t1\n"}


@pytest.mark.parametrize(
    ("bodies", "call"),
    [
        pytest.param(
            {**DAILY_OK, "daily": "fastapi\t2024-13-01:1\n"},
            lambda s: s.daily_downloads(["fastapi"], *JANUARY),
            id="daily-non-iso-date",
        ),
        pytest.param(
            {**DAILY_OK, "daily": "fastapi\n"},
            lambda s: s.daily_downloads(["fastapi"], *JANUARY),
            id="daily-missing-field",
        ),
        pytest.param(
            {**DAILY_OK, "checksums": "fastapi\tuno\t1\n"},
            lambda s: s.daily_downloads(["fastapi"], *JANUARY),
            id="daily-checksum-not-a-number",
        ),
        pytest.param(
            {**TOTALS, "totals": "2024-01-01:cien\n"},
            lambda s: s.pypi_daily_totals(*JANUARY),
            id="totals-count-not-a-number",
        ),
        pytest.param(
            {**TOTALS, "totals_checksums": "2\n"},
            lambda s: s.pypi_daily_totals(*JANUARY),
            id="totals-checksum-missing-field",
        ),
        pytest.param(
            {"top": "dos mil\trequests\t9\n"},
            lambda s: s.top_projects([2017], n=1),
            id="top-year-not-a-number",
        ),
    ],
)
def test_a_malformed_body_is_a_source_error(bodies, call):
    with pytest.raises(SourceError):
        call(ClickPy(answering(bodies)))


@pytest.mark.parametrize(
    "item",
    [f"2024-01-01{US}3.12", f"2024-01-01{US}3{US}12{US}5"],
    ids=["two-fields", "separator-inside-the-version"],
)
def test_a_python_row_without_exactly_three_fields_is_a_source_error(item):
    bodies = python_bodies(python=by_range({m: f"{item}\n" for m in ("", "d", "m", "s")}))

    with pytest.raises(SourceError):
        ClickPy(answering(bodies)).python_minor_monthly(before=date(2024, 3, 1))
