"""Garantías de los workflows de GitHub Actions (PRD, historia 48): se leen como datos."""

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).parent.parent / ".github" / "workflows"
SHA_PIN = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")


def load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text())


def triggers(workflow: dict) -> dict:
    # YAML 1.1 lee la clave `on` como True.
    return workflow.get("on", workflow.get(True)) or {}


def steps(job: dict) -> list[dict]:
    return job.get("steps", [])


def all_workflows() -> list[str]:
    return sorted(p.name for p in WORKFLOWS.glob("*.yml"))


def test_there_is_an_update_workflow_and_a_ci_workflow():
    assert all_workflows() == ["ci.yml", "update.yml"]


@pytest.mark.parametrize("name", ["ci.yml", "update.yml"])
def test_every_action_is_pinned_to_a_full_commit_sha_with_its_version(name):
    text = (WORKFLOWS / name).read_text()
    uses = re.findall(r"uses:\s*(\S+)(.*)", text)

    assert uses
    for action, rest in uses:
        assert SHA_PIN.match(action), action
        assert re.search(r"#\s*v\d+\.\d+\.\d+", rest), f"{action} sin versión comentada"


@pytest.mark.parametrize("name", ["ci.yml", "update.yml"])
def test_no_workflow_runs_on_pull_request_target_and_none_grants_by_default(name):
    workflow = load(name)

    assert "pull_request_target" not in triggers(workflow)
    assert workflow["permissions"] == {}


def test_only_the_update_job_can_write_to_the_repository():
    jobs = {**load("update.yml")["jobs"], **load("ci.yml")["jobs"]}

    writers = {name for name, job in jobs.items() if "write" in job.get("permissions", {}).values()}

    assert writers == {"update"}
    assert load("update.yml")["jobs"]["update"]["permissions"] == {"contents": "write"}


def test_cloudflare_secrets_reach_only_the_deploy_job_which_runs_no_repository_code():
    jobs = load("update.yml")["jobs"]

    for name, job in jobs.items():
        mentions = "secrets." in yaml.safe_dump(job)
        assert mentions == (name == "deploy"), name
    deploy = jobs["deploy"]
    assert not any("run" in step for step in steps(deploy))
    assert not any("checkout" in step.get("uses", "") for step in steps(deploy))
    assert deploy["environment"] == "production"


def test_the_write_job_restores_no_cache():
    update = load("update.yml")["jobs"]["update"]

    setup = next(s for s in steps(update) if "setup-uv" in s.get("uses", ""))

    assert setup["with"]["enable-cache"] is False


def test_downloads_update_daily_and_stars_weekly():
    workflow = load("update.yml")
    crons = [entry["cron"] for entry in triggers(workflow)["schedule"]]
    update = workflow["jobs"]["update"]

    stars = next(s for s in steps(update) if "ecopy stars" in s.get("run", ""))

    assert len(crons) == 2
    daily, weekly = crons
    assert daily.split()[2:] == ["*", "*", "*"]
    assert weekly.split()[2:4] == ["*", "*"] and weekly.split()[4] != "*"
    assert weekly in stars["if"]
    assert "--budget" in stars["run"]
    assert "workflow_dispatch" in triggers(workflow)


def test_a_failed_ingest_still_publishes_the_notice_but_fails_the_run():
    jobs = load("update.yml")["jobs"]
    update = jobs["update"]

    ingest = next(s for s in steps(update) if s.get("run", "").strip() == "uv run ecopy ingest")
    order = [s.get("run", "") for s in steps(update)]

    assert ingest["continue-on-error"] is True
    assert update["outputs"]["ingest"] == f"${{{{ steps.{ingest['id']}.outcome }}}}"
    assert order.index(ingest["run"]) < next(i for i, r in enumerate(order) if "ecopy build" in r)
    report = jobs["report"]
    assert set(report["needs"]) == {"update", "deploy"}
    assert "needs.update.outputs.ingest" in report["if"]


def test_wrangler_is_pinned_to_an_exact_version():
    deploy = load("update.yml")["jobs"]["deploy"]

    wrangler = next(s for s in steps(deploy) if "wrangler-action" in s.get("uses", ""))

    assert re.fullmatch(r"\d+\.\d+\.\d+", wrangler["with"]["wranglerVersion"])
    assert "pages deploy" in wrangler["with"]["command"]


def test_runs_never_overlap_on_the_data():
    workflow = load("update.yml")

    assert workflow["concurrency"] == {"group": "data", "cancel-in-progress": False}


def test_ci_checks_lint_format_and_tests_with_read_only_access():
    workflow = load("ci.yml")
    job = workflow["jobs"]["test"]
    commands = " ".join(s.get("run", "") for s in steps(job))

    assert "pull_request" in triggers(workflow)
    assert job["permissions"] == {"contents": "read"}
    for command in ("uv sync --locked", "ruff check", "ruff format --check", "pytest"):
        assert command in commands
    checkout = next(s for s in steps(job) if "checkout" in s.get("uses", ""))
    assert checkout["with"]["persist-credentials"] is False


def test_publishing_jobs_run_only_from_main():
    jobs = load("update.yml")["jobs"]

    for name in ("update", "deploy"):
        assert jobs[name]["if"] == "github.ref == 'refs/heads/main'", name


def test_the_update_checks_out_main_without_keeping_the_token_in_git():
    update = load("update.yml")["jobs"]["update"]

    checkout = next(s for s in steps(update) if "checkout" in s.get("uses", ""))

    assert checkout["with"]["ref"] == "main"
    assert checkout["with"]["persist-credentials"] is False


def test_the_token_reaches_only_the_push_and_the_github_stars_steps():
    update = load("update.yml")["jobs"]["update"]

    holders = {
        step.get("name") or step.get("id") or step.get("uses") or step["run"]
        for step in steps(update)
        if "github.token" in yaml.safe_dump(step)
    }

    assert holders == {"Commit de datos", "stars"}
    assert "github.token" not in yaml.safe_dump({k: v for k, v in update.items() if k != "steps"})
    push = next(s for s in steps(update) if s.get("name") == "Commit de datos")
    assert "github.token" in push["env"]["REMOTE"]


def git(cwd: Path, *args: str) -> str:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    done = subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True)
    return done.stdout.decode().strip()


@pytest.fixture
def checkout(tmp_path):
    """Un `origin` bare con `main` y un clon como el que deja actions/checkout."""
    seed, origin, work = tmp_path / "seed", tmp_path / "origin.git", tmp_path / "work"
    seed.mkdir()
    git(seed, "init", "-q", "-b", "main")
    (seed / "data").mkdir()
    (seed / "data" / "runs.json").write_text("[]")
    (seed / "README.md").write_text("ecopy")
    git(seed, "add", ".")
    git(seed, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "inicio")
    git(tmp_path, "clone", "-q", "--bare", str(seed), str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(work))
    # Sin credenciales persistidas, `origin` no sirve para empujar: solo `$REMOTE`.
    git(work, "remote", "set-url", "origin", str(tmp_path / "sin-credenciales.git"))
    return origin, work


def push_data(work: Path, origin: Path) -> subprocess.CompletedProcess:
    update = load("update.yml")["jobs"]["update"]
    script = next(s for s in steps(update) if s.get("name") == "Commit de datos")["run"]
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "REMOTE": str(origin)}
    return subprocess.run(["bash", "-e", "-c", script], cwd=work, env=env, capture_output=True)


def test_the_push_carries_only_the_new_data_commit(checkout):
    origin, work = checkout
    before = git(origin, "rev-parse", "main")
    (work / "data" / "runs.json").write_text("[1]")

    assert push_data(work, origin).returncode == 0

    assert git(origin, "rev-list", "--count", f"{before}..main") == "1"
    assert git(origin, "diff", "--name-only", before, "main").split() == ["data/runs.json"]


def test_a_commit_outside_data_is_never_pushed_to_main(checkout):
    origin, work = checkout
    before = git(origin, "rev-parse", "main")
    (work / "README.md").write_text("cambio sin revisar")
    git(work, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "no es de datos")
    (work / "data" / "runs.json").write_text("[1]")

    assert push_data(work, origin).returncode != 0

    assert git(origin, "rev-parse", "main") == before


def test_stars_stop_on_their_own_before_the_step_times_out():
    update = load("update.yml")["jobs"]["update"]

    stars = next(s for s in steps(update) if "ecopy stars" in s.get("run", ""))
    minutes = float(re.search(r"--max-minutes (\d+)", stars["run"]).group(1))

    assert minutes + 3 <= stars["timeout-minutes"] < update["timeout-minutes"]
