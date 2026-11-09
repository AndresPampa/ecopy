"""CLI: la política de ingesta y el recorrido completo, de la fuente a las páginas."""

import json
import re
import subprocess
import threading
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pyarrow.parquet as pq
import pytest

from ecopy.cli import ingest_window, main, make_server

FIXTURE = Path(__file__).parent / "fixtures" / "clickpy" / "fastapi_2024-01.json"
SINCE = date(2016, 1, 22)
NOW = datetime(2024, 2, 1, 1, 0, tzinfo=UTC)
TAG = re.compile(r"/\* ecopy:(\w+) \*/")


def test_version_command_reports_package_name_and_version():
    result = subprocess.run(["ecopy", "--version"], capture_output=True, text=True, check=False)

    assert result.returncode == 0
    assert result.stdout.strip() == "ecopy 0.1.0"


def test_a_project_without_data_is_backfilled_until_yesterday_utc():
    window = ingest_window(None, SINCE, NOW)

    assert (window.start, window.end, window.acquisition) == (SINCE, date(2024, 1, 31), "backfill")


def test_a_project_with_data_continues_from_the_day_after_the_last_saved():
    window = ingest_window(date(2024, 1, 20), SINCE, NOW)

    assert (window.start, window.end, window.acquisition) == (
        date(2024, 1, 21),
        date(2024, 1, 31),
        "observed",
    )


def test_a_project_up_to_date_needs_no_ingestion():
    assert ingest_window(date(2024, 1, 31), SINCE, NOW) is None


def recorded_clickpy() -> httpx.Client:
    exchanges = json.loads(FIXTURE.read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        recorded = exchanges[TAG.search(request.content.decode()).group(1)]
        headers = {"X-ClickHouse-Summary": json.dumps(recorded["summary"])}
        return httpx.Response(200, headers=headers, text=recorded["body"])

    return httpx.Client(transport=httpx.MockTransport(handler))


def ingest(data, http) -> int:
    return main(["ingest", "--project", "fastapi", "--data", str(data)], http=http, now=lambda: NOW)


def build(data, out) -> int:
    return main(["build", "--project", "fastapi", "--data", str(data), "--out", str(out)])


def test_ingest_and_build_produce_the_library_pages(tmp_path):
    data, out = tmp_path / "data", tmp_path / "site"

    assert ingest(data, recorded_clickpy()) == 0
    assert build(data, out) == 0

    english = (out / "en" / "library" / "fastapi" / "index.html").read_text()
    spanish = (out / "es" / "library" / "fastapi" / "index.html").read_text()
    assert "35,561,750" in english
    assert "35.561.750" in spanish
    assert "default-src 'none'" in (out / "_headers").read_text()
    [written] = list(data.rglob("*.parquet"))
    assert pq.read_table(written).to_pylist()[0]["acquisition"] == "backfill"


def test_ingesting_again_on_the_same_day_does_not_call_the_source(tmp_path):
    data = tmp_path / "data"
    ingest(data, recorded_clickpy())

    def unexpected(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no debería consultar la fuente")

    assert ingest(data, httpx.Client(transport=httpx.MockTransport(unexpected))) == 0
    assert len(list(data.rglob("*.parquet"))) == 1


def test_a_source_failure_exits_with_an_error_and_writes_nothing(tmp_path, capsys):
    data = tmp_path / "data"
    down = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(400, text="no")))

    assert ingest(data, down) == 1

    assert "ecopy:" in capsys.readouterr().err
    assert not list(data.rglob("*.parquet"))


def test_building_without_data_exits_with_an_error(tmp_path, capsys):
    assert build(tmp_path / "data", tmp_path / "site") == 1

    assert "ingest" in capsys.readouterr().err


def test_serve_applies_the_csp_of_the_built_site(tmp_path):
    data, out = tmp_path / "data", tmp_path / "site"
    ingest(data, recorded_clickpy())
    build(data, out)

    server = make_server(out, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}/en/library/fastapi/"
        response = httpx.get(url, trust_env=False)
    finally:
        server.shutdown()
        server.server_close()

    assert response.status_code == 200
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_serve_requires_a_built_site(tmp_path):
    with pytest.raises(FileNotFoundError):
        make_server(tmp_path / "missing", port=0)


def empty_clickpy() -> httpx.Client:
    summary = {"read_rows": "0", "total_rows_to_read": "0", "result_bytes": "0"}

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"X-ClickHouse-Summary": json.dumps(summary)}, text="")

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_an_unknown_package_exits_with_an_error(tmp_path):
    assert ingest(tmp_path / "data", empty_clickpy()) == 1


def test_a_known_package_without_new_days_is_not_an_error(tmp_path):
    data = tmp_path / "data"
    ingest(data, recorded_clickpy())
    later = datetime(2024, 2, 5, tzinfo=UTC)

    args = ["ingest", "--project", "fastapi", "--data", str(data)]
    assert main(args, http=empty_clickpy(), now=lambda: later) == 0
