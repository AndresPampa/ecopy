"""CLI: la política de ingesta y el recorrido completo, de la fuente a las páginas."""

import json
import re
import subprocess
import threading
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pyarrow.parquet as pq
import pytest
import yaml

from ecopy.cli import main, make_server

FIXTURE = Path(__file__).parent / "fixtures" / "clickpy" / "fastapi_2024-01.json"
NOW = datetime(2024, 2, 1, 1, 0, tzinfo=UTC)
TAG = re.compile(r"/\* ecopy:(\w+) \*/")


def test_version_command_reports_package_name_and_version():
    result = subprocess.run(["ecopy", "--version"], capture_output=True, text=True, check=False)

    assert result.returncode == 0
    assert result.stdout.strip() == "ecopy 0.1.0"


JANUARY = [date(2024, 1, day) for day in range(1, 32)]
DAILY_TOTAL = 10**9
# El replay no ejecuta SQL: los totales coherentes con la fixture real de `fastapi`.
SYNTHETIC = {
    "totals": ",".join(f"{day}:{DAILY_TOTAL}" for day in JANUARY) + "\n",
    "totals_checksums": f"31\t{31 * DAILY_TOTAL}\n",
    "python": f"2024-01-01\x1f3.12\x1f{31 * DAILY_TOTAL}\n",
    "python_checksums": f"{31 * DAILY_TOTAL}\n",
    "known": "fastapi\n",
}
SUMMARY = {"read_rows": "1", "total_rows_to_read": "1", "result_bytes": "1"}


def clickpy_answering(overrides=None) -> httpx.Client:
    exchanges = json.loads(FIXTURE.read_text())
    answers = {**SYNTHETIC, **(overrides or {})}

    def handler(request: httpx.Request) -> httpx.Response:
        sql = request.content.decode()
        tag = TAG.search(sql).group(1)
        if tag in exchanges and tag not in answers:
            recorded = exchanges[tag]
            headers = {"X-ClickHouse-Summary": json.dumps(recorded["summary"])}
            return httpx.Response(200, headers=headers, text=recorded["body"])
        body = answers[tag]
        if tag.startswith("python") and "project >= ''" not in sql:
            body = "0\n" if tag.endswith("checksums") else ""
        return httpx.Response(200, headers={"X-ClickHouse-Summary": json.dumps(SUMMARY)}, text=body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def recorded_clickpy() -> httpx.Client:
    return clickpy_answering()


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
    downloads = next((data / "raw" / "clickpy" / "downloads_daily").rglob("*.parquet"))
    assert pq.read_table(downloads).to_pylist()[0]["acquisition"] == "backfill"
    assert (data / "raw" / "clickpy" / "pypi_total_daily").is_dir()
    assert (data / "raw" / "clickpy" / "python_minor_monthly").is_dir()


def test_ingesting_again_reobserves_and_writes_no_new_data(tmp_path):
    data = tmp_path / "data"
    assert ingest(data, recorded_clickpy()) == 0
    files = sorted(data.rglob("*.parquet"))

    args = ["ingest", "--project", "fastapi", "--data", str(data)]
    later = NOW + timedelta(hours=1)
    assert main(args, http=recorded_clickpy(), now=lambda: later) == 0

    assert sorted(data.rglob("*.parquet")) == files
    assert len(list((data / "runs").glob("*.json"))) == 2


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


EMPTY = {
    "daily": "",
    "checksums": "",
    "totals": "\n",
    "totals_checksums": "0\t0\n",
    "python": "",
    "python_checksums": "0\n",
}


def empty_clickpy() -> httpx.Client:
    return clickpy_answering(EMPTY)


def test_an_unknown_package_exits_with_an_error(tmp_path, capsys):
    assert ingest(tmp_path / "data", empty_clickpy()) == 1

    assert "unknown_project" in capsys.readouterr().err


def test_a_known_package_without_new_days_is_not_an_error(tmp_path):
    data = tmp_path / "data"
    ingest(data, recorded_clickpy())
    later = datetime(2024, 2, 3, tzinfo=UTC)

    args = ["ingest", "--project", "fastapi", "--data", str(data)]
    assert main(args, http=empty_clickpy(), now=lambda: later) == 0


CATALOG_TAXONOMY = {
    "domains": [
        {
            "slug": "d",
            "en": "D",
            "es": "D",
            "categories": [{"slug": "web", "en": "Web", "es": "Web"}],
        }
    ],
    "tags": [],
}


def write_catalog(root, *projects: str, top=None):
    root.mkdir(exist_ok=True)
    (root / "taxonomy.yaml").write_text(yaml.safe_dump(CATALOG_TAXONOMY))
    libraries = [{"project": p, "category": "web"} for p in projects]
    (root / "libraries.yaml").write_text(yaml.safe_dump(libraries))
    (root / "top100.yaml").write_text(yaml.safe_dump(top or {"years": {}}))
    return root


def test_without_project_flags_the_whole_catalog_is_ingested_and_built(tmp_path):
    data, out, catalog = (
        tmp_path / "data",
        tmp_path / "site",
        write_catalog(tmp_path / "c", "fastapi"),
    )
    options = ["--data", str(data), "--catalog", str(catalog)]

    assert main(["ingest", *options], http=recorded_clickpy(), now=lambda: NOW) == 0
    assert main(["build", *options, "--out", str(out)]) == 0

    assert (out / "en" / "library" / "fastapi" / "index.html").exists()


def test_a_package_without_data_is_skipped_when_building(tmp_path, capsys):
    data, out = tmp_path / "data", tmp_path / "site"
    ingest(data, recorded_clickpy())
    catalog = write_catalog(tmp_path / "c", "fastapi", "other")

    args = ["build", "--data", str(data), "--catalog", str(catalog), "--out", str(out)]
    assert main(args) == 0

    assert "other" in capsys.readouterr().err
    assert (out / "en" / "library" / "fastapi" / "index.html").exists()
    assert not (out / "en" / "library" / "other").exists()


def test_an_invalid_catalog_exits_with_its_problems(tmp_path, capsys):
    catalog = write_catalog(tmp_path / "c", "fastapi", top={"years": {2024: ["urllib3"]}})

    code = main(["build", "--data", str(tmp_path), "--catalog", str(catalog)])

    assert code == 1
    assert "urllib3" in capsys.readouterr().err


def test_a_rejected_run_rebuilds_the_previous_figures_with_the_notice(tmp_path, capsys):
    data, out = tmp_path / "data", tmp_path / "site"
    assert ingest(data, recorded_clickpy()) == 0
    collapsed = clickpy_answering(
        {"totals": "2024-02-01:1\n", "totals_checksums": "1\t1\n"},
    )
    next_day = datetime(2024, 2, 2, 1, tzinfo=UTC)

    args = ["ingest", "--project", "fastapi", "--data", str(data)]
    assert main(args, http=collapsed, now=lambda: next_day) == 1
    assert "volume" in capsys.readouterr().err
    assert build(data, out) == 0

    english = (out / "en" / "library" / "fastapi" / "index.html").read_text()
    spanish = (out / "es" / "library" / "fastapi" / "index.html").read_text()
    assert "Update failed" in english
    assert "Actualización fallida" in spanish
    assert "35,561,750" in english
    assert "2024-02-01" in english


def test_validate_reports_a_healthy_and_a_stale_store(tmp_path, capsys):
    data, catalog = tmp_path / "data", write_catalog(tmp_path / "c", "fastapi")
    ingest(data, recorded_clickpy())
    options = ["validate", "--data", str(data), "--catalog", str(catalog)]

    assert main(options, now=lambda: NOW) == 0
    later = datetime(2024, 3, 1, tzinfo=UTC)
    assert main(options, now=lambda: later) == 1

    assert "stale" in capsys.readouterr().err


def test_catalog_check_fails_for_a_package_the_source_does_not_have(tmp_path, capsys):
    catalog = write_catalog(tmp_path / "c", "fastapi", "tkinter")

    code = main(["catalog", "check", "--catalog", str(catalog)], http=recorded_clickpy())

    assert code == 1
    assert "tkinter" in capsys.readouterr().err


def test_catalog_refresh_writes_the_ranking(tmp_path, capsys):
    catalog = tmp_path / "c"
    catalog.mkdir()
    years = range(2017, 2025)

    def top(sql: str) -> str:
        wanted = re.search(r"IN \(([\d, ]+)\)", sql).group(1).split(", ")
        return "".join(f"{y}\t{p}\t1\n" for y in wanted for p in [f"p{i}" for i in range(100)])

    def handler(request: httpx.Request) -> httpx.Response:
        headers = {"X-ClickHouse-Summary": json.dumps(SUMMARY)}
        return httpx.Response(200, headers=headers, text=top(request.content.decode()))

    http = httpx.Client(transport=httpx.MockTransport(handler))
    code = main(["catalog", "refresh", "--catalog", str(catalog)], http=http, now=lambda: NOW)

    assert code == 0
    saved = yaml.safe_load((catalog / "top100.yaml").read_text())["years"]
    assert sorted(saved) == list(years)
    assert "100" in capsys.readouterr().out
