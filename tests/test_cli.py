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
from ecopy.models import DailyDownload, DailyTotal, DownloadBatch, PypiTotalsBatch, Run
from ecopy.store import Store

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


def test_a_response_without_summary_is_recorded_as_a_failed_run(tmp_path, capsys):
    data = tmp_path / "data"
    bare = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, text="")))

    assert ingest(data, bare) == 1

    assert "ecopy:" in capsys.readouterr().err
    assert [run.status for run in Store(data).runs()] == ["failed"]
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


@pytest.mark.parametrize(
    ("path", "text"), [("/en/nope/", "Page not found"), ("/es/nada/", "Página no encontrada")]
)
def test_serve_answers_a_missing_page_with_the_site_404_in_its_language(tmp_path, path, text):
    data, out = tmp_path / "data", tmp_path / "site"
    ingest(data, recorded_clickpy())
    build(data, out)

    server = make_server(out, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}{path}"
        response = httpx.get(url, trust_env=False)
    finally:
        server.shutdown()
        server.server_close()

    assert response.status_code == 404
    assert text in response.text
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]


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


def write_catalog(root, *projects: str, top=None, repos=None):
    root.mkdir(exist_ok=True)
    (root / "taxonomy.yaml").write_text(yaml.safe_dump(CATALOG_TAXONOMY))
    libraries = [{"project": p, "category": "web"} for p in projects]
    (root / "libraries.yaml").write_text(yaml.safe_dump(libraries))
    (root / "repos.yaml").write_text(
        yaml.safe_dump({"repos": {p: (repos or {}).get(p) for p in projects}})
    )
    (root / "top100.yaml").write_text(yaml.safe_dump(top or {"years": {}}))
    (root / "python_releases.yaml").write_text(
        yaml.safe_dump({"releases": [{"version": "3.12", "released": date(2023, 10, 2)}]})
    )
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


def seed(store: Store, *, through: date = date(2024, 1, 15), category_project: str = "fastapi"):
    run = Run("seed", datetime(2024, 2, 1, tzinfo=UTC), "backfill")
    days = [date(2023, 6, 1), date(2023, 12, 31), through]
    store.append(
        DownloadBatch("clickpy", tuple(DailyDownload(category_project, d, 10) for d in days)), run
    )
    store.append(PypiTotalsBatch("clickpy", tuple(DailyTotal(d, 100) for d in days)), run)


def yearly_catalog(root, top=None):
    return write_catalog(root, "fastapi", top=top or {"years": {2023: ["fastapi"]}})


def test_a_full_build_needs_the_closed_years_frozen(tmp_path, capsys):
    data = tmp_path / "data"
    seed(Store(data))
    catalog = yearly_catalog(tmp_path / "c")

    code = main(
        ["build", "--data", str(data), "--catalog", str(catalog), "--out", str(tmp_path / "s")]
    )

    assert code == 1
    assert "ecopy freeze" in capsys.readouterr().err


def test_freezing_lets_a_full_build_write_every_year(tmp_path):
    data, out = tmp_path / "data", tmp_path / "site"
    seed(Store(data))
    catalog = yearly_catalog(tmp_path / "c")
    options = ["--data", str(data), "--catalog", str(catalog)]

    assert main(["freeze", *options]) == 0
    assert main(["build", *options, "--out", str(out)]) == 0

    assert (data / "frozen" / "year=2023" / "methodology=1.json").exists()
    assert not (data / "frozen" / "year=2024").exists()
    assert (out / "en" / "year" / "2023" / "index.html").exists()
    assert (out / "es" / "year" / "2024" / "index.html").exists()
    assert (out / "en" / "index.html").exists()


def test_freezing_twice_is_harmless_and_keeps_the_file(tmp_path, capsys):
    data = tmp_path / "data"
    seed(Store(data))
    catalog = yearly_catalog(tmp_path / "c")
    options = ["freeze", "--data", str(data), "--catalog", str(catalog)]
    main(options)
    frozen = data / "frozen" / "year=2023" / "methodology=1.json"
    before = frozen.read_bytes()

    assert main(options) == 0

    assert frozen.read_bytes() == before
    assert "0 años" in capsys.readouterr().out


def test_a_frozen_year_does_not_change_when_the_catalog_does(tmp_path):
    data, out = tmp_path / "data", tmp_path / "site"
    seed(Store(data))
    catalog = yearly_catalog(tmp_path / "c")
    main(["freeze", "--data", str(data), "--catalog", str(catalog)])
    (catalog / "top100.yaml").write_text(yaml.safe_dump({"years": {2023: []}}))
    frozen = (data / "frozen" / "year=2023" / "methodology=1.json").read_bytes()

    main(["build", "--data", str(data), "--catalog", str(catalog), "--out", str(out)])

    assert (data / "frozen" / "year=2023" / "methodology=1.json").read_bytes() == frozen


def test_freezing_needs_the_ranking_of_the_year(tmp_path, capsys):
    data = tmp_path / "data"
    seed(Store(data))
    catalog = yearly_catalog(tmp_path / "c", top={"years": {}})

    assert main(["freeze", "--data", str(data), "--catalog", str(catalog)]) == 1

    assert "catalog refresh" in capsys.readouterr().err


def test_a_single_project_build_writes_no_year_pages(tmp_path):
    data, out = tmp_path / "data", tmp_path / "site"
    seed(Store(data))

    args = ["build", "--project", "fastapi", "--data", str(data), "--out", str(out)]
    assert main(args) == 0

    assert not (out / "en" / "year").exists()


def test_a_dormant_package_uses_the_same_as_of_as_the_rest(tmp_path):
    data, out = tmp_path / "data", tmp_path / "site"
    run = Run("seed", datetime(2024, 4, 1, tzinfo=UTC), "backfill")
    rows = (
        DailyDownload("old", date(2024, 1, 10), 1),
        DailyDownload("alive", date(2024, 3, 31), 1),
    )
    Store(data).append(DownloadBatch("clickpy", rows), run)
    args = [
        "build",
        "--project",
        "old",
        "--project",
        "alive",
        "--data",
        str(data),
        "--out",
        str(out),
    ]

    assert main(args) == 0

    assert ">2024-03<" in (out / "en" / "library" / "old" / "index.html").read_text()


WEEK = int(datetime(2024, 1, 7, tzinfo=UTC).timestamp())


def github() -> tuple[httpx.Client, list[httpx.Request]]:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path.endswith("/history"):
            return httpx.Response(200, json=[{"week": WEEK, "total": 7, "days": [7] + [0] * 6}])
        return httpx.Response(200, json={"full_name": "fastapi/fastapi", "stargazers_count": 7})

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


def stars(catalog, data, http, *extra) -> int:
    return main(
        ["stars", "--catalog", str(catalog), "--data", str(data), *extra],
        http=http,
        now=lambda: NOW,
        sleep=lambda _: None,
    )


def test_stars_uses_the_token_and_saves_the_history(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "s3cret")
    catalog = write_catalog(tmp_path / "c", "fastapi", repos={"fastapi": "fastapi/fastapi"})
    client, calls = github()

    assert stars(catalog, tmp_path / "d", client) == 0

    assert calls[0].headers["authorization"] == "Bearer s3cret"
    assert Store(tmp_path / "d").backfilled_repos() == {"fastapi/fastapi"}
    output = capsys.readouterr()
    assert "1 con historia completa" in output.out
    assert "s3cret" not in output.out + output.err


def test_without_a_token_stars_warns_and_caps_its_requests(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    names = [f"p{i}" for i in range(40)]
    catalog = write_catalog(tmp_path / "c", *names, repos={n: f"o/{n}" for n in names})
    client, calls = github()

    assert stars(catalog, tmp_path / "d", client, "--budget", "4000") == 0

    assert len(calls) == 50
    assert "GITHUB_TOKEN" in capsys.readouterr().err


def test_stars_can_be_limited_to_repos_of_the_catalog(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    catalog = write_catalog(tmp_path / "c", "fastapi", repos={"fastapi": "fastapi/fastapi"})

    assert stars(catalog, tmp_path / "d", github()[0], "--repo", "no/such") == 1

    assert "no/such" in capsys.readouterr().err


def test_a_star_run_does_not_change_the_last_update_of_the_site(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    catalog = write_catalog(tmp_path / "c", "fastapi", repos={"fastapi": "fastapi/fastapi"})

    stars(catalog, tmp_path / "d", github()[0])

    assert Store(tmp_path / "d").runs() == ()


def test_a_full_build_writes_the_catalog_pages_and_shows_the_stars(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    data = tmp_path / "d"
    catalog = yearly_catalog(tmp_path / "c")
    (catalog / "repos.yaml").write_text(yaml.safe_dump({"repos": {"fastapi": "fastapi/fastapi"}}))
    seed(Store(data))
    assert main(["freeze", "--catalog", str(catalog), "--data", str(data)]) == 0
    stars(catalog, data, github()[0])
    out = tmp_path / "site"

    assert main(["build", "--catalog", str(catalog), "--data", str(data), "--out", str(out)]) == 0

    assert (out / "en" / "library" / "index.html").exists()
    assert (out / "en" / "compare" / "index.html").exists()
    assert (out / "es" / "python" / "index.html").exists()
    assert (out / "en" / "category" / "web" / "index.html").exists()
    assert (out / "data" / "library" / "fastapi.json").exists()
    assert "7 stars in fastapi/fastapi" in (out / "en/library/fastapi/index.html").read_text()


def test_a_shared_repo_lists_only_the_other_packages(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    data, out = tmp_path / "d", tmp_path / "site"
    repos = {"fastapi": "fastapi/fastapi", "flask": "fastapi/fastapi"}
    catalog = write_catalog(tmp_path / "c", "fastapi", "flask", repos=repos)
    run = Run("seed", datetime(2024, 2, 1, tzinfo=UTC), "backfill")
    rows = tuple(DailyDownload(p, date(2024, 1, 15), 10) for p in ("fastapi", "flask"))
    Store(data).append(DownloadBatch("clickpy", rows), run)
    Store(data).append(PypiTotalsBatch("clickpy", (DailyTotal(date(2024, 1, 15), 100),)), run)
    stars(catalog, data, github()[0])

    assert main(["build", "--catalog", str(catalog), "--data", str(data), "--out", str(out)]) == 0

    html = (out / "en" / "library" / "fastapi" / "index.html").read_text()
    shared = html[html.index("also publishes") :]
    assert 'href="/en/library/flask/"' in shared[:200]
    assert 'href="/en/library/fastapi/"' not in shared[:200]


def test_stars_stops_and_saves_when_its_time_runs_out(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    catalog = write_catalog(tmp_path / "c", "fastapi", repos={"fastapi": "fastapi/fastapi"})
    client, calls = github()

    assert stars(catalog, tmp_path / "d", client, "--max-minutes", "0") == 0

    assert calls == []
    out = capsys.readouterr().out
    assert "1 pendientes" in out
    assert "se detuvo (rate_limited)" in out


def test_catalog_starts_writes_the_series_starts_from_pypi(tmp_path, capsys):
    data, catalog = tmp_path / "data", write_catalog(tmp_path / "c", "fastapi")
    seed(Store(data))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/pypi/fastapi/json"
        upload = {"upload_time_iso_8601": "2024-01-10T00:00:00.000000Z"}
        return httpx.Response(200, json={"releases": {"1": [upload]}})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    code = main(["catalog", "starts", "--catalog", str(catalog), "--data", str(data)], http=http)

    assert code == 0
    saved = yaml.safe_load((catalog / "series_start.yaml").read_text())
    assert saved == {"starts": {"fastapi": date(2024, 1, 10)}}
    assert "fastapi" in capsys.readouterr().out
