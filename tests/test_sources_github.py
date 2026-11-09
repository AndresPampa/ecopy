"""Adaptador de GitHub: historia de estrellas con paginación, cuadre y límites de la API."""

from datetime import UTC, date, datetime

import httpx
import pytest

from ecopy.sources.clickpy import SourceError
from ecopy.sources.github import BudgetExhausted, GitHub, RateLimited

WEEK_1 = int(datetime(2024, 1, 7, tzinfo=UTC).timestamp())
WEEK_2 = int(datetime(2024, 1, 14, tzinfo=UTC).timestamp())


def week(when: int, total: int) -> dict:
    return {"week": when, "total": total, "days": [total, 0, 0, 0, 0, 0, 0]}


def answer(routes: dict, headers: dict | None = None):
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        key = request.url.path
        if key.endswith("/history"):
            key = f"{key}?{request.url.params['page']}"
        body = routes[key]
        if isinstance(body, httpx.Response):
            return body
        return httpx.Response(200, json=body, headers=headers or {})

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


REPO = {"full_name": "a/b", "stargazers_count": 15, "owner": {"login": "someone"}}
ROUTES = {
    "/repos/a/b": REPO,
    "/repos/a/b/stargazers/history?1": [week(WEEK_2, 5), week(WEEK_1, 10)],
}


def source(client, **options) -> GitHub:
    return GitHub(client, sleep=lambda _: None, **options)


def test_the_full_history_returns_weeks_and_the_current_count():
    client, _ = answer(ROUTES)

    stars = source(client).full_history("a/b")

    assert (stars.repo, stars.full_name, stars.stars) == ("a/b", "a/b", 15)
    assert [(w.repo, w.week, w.stars) for w in stars.weeks] == [
        ("a/b", date(2024, 1, 7), 10),
        ("a/b", date(2024, 1, 14), 5),
    ]


def test_the_history_follows_pages_until_a_short_one():
    page = [week(WEEK_1 - 604800 * i, 1) for i in range(30)]
    routes = {
        "/repos/a/b": {**REPO, "stargazers_count": 31},
        "/repos/a/b/stargazers/history?1": page,
        "/repos/a/b/stargazers/history?2": [week(WEEK_1 - 604800 * 30, 1)],
    }
    client, calls = answer(routes)

    stars = source(client).full_history("a/b")

    assert len(stars.weeks) == 31
    assert len(calls) == 3


def test_recent_reads_only_the_first_page():
    page = [week(WEEK_1 - 604800 * i, 1) for i in range(30)]
    client, calls = answer({"/repos/a/b": REPO, "/repos/a/b/stargazers/history?1": page})

    assert len(source(client).recent("a/b").weeks) == 30
    assert len(calls) == 2


def test_a_history_that_does_not_add_up_is_an_error():
    routes = {**ROUTES, "/repos/a/b": {**REPO, "stargazers_count": 100}}
    client, _ = answer(routes)

    with pytest.raises(SourceError, match="a/b"):
        source(client).full_history("a/b")


def test_a_star_arriving_while_paginating_is_tolerated():
    routes = {**ROUTES, "/repos/a/b": {**REPO, "stargazers_count": 18}}
    client, _ = answer(routes)

    assert source(client).full_history("a/b").stars == 18


def test_a_moved_repo_reports_its_canonical_name():
    routes = {**ROUTES, "/repos/a/b": {**REPO, "full_name": "new/b"}}
    client, _ = answer(routes)

    assert source(client).full_history("a/b").full_name == "new/b"


def test_a_missing_repo_is_a_source_error():
    client, _ = answer({"/repos/a/b": httpx.Response(404, json={})})

    with pytest.raises(SourceError, match="404"):
        source(client).full_history("a/b")


def test_the_token_goes_in_the_header_and_never_in_an_error():
    client, calls = answer({"/repos/a/b": httpx.Response(500, json={})})

    with pytest.raises(SourceError) as error:
        source(client, token="s3cret").full_history("a/b")

    assert calls[0].headers["authorization"] == "Bearer s3cret"
    assert "s3cret" not in str(error.value)


def test_requests_stop_at_the_budget():
    client, calls = answer(ROUTES)

    with pytest.raises(BudgetExhausted):
        source(client, budget=1).full_history("a/b")

    assert len(calls) == 1


def test_requests_stop_when_the_quota_runs_low():
    client, calls = answer(ROUTES, headers={"x-ratelimit-remaining": "50"})

    with pytest.raises(BudgetExhausted):
        source(client, token="t").full_history("a/b")

    assert len(calls) == 1


def test_a_quota_of_zero_raises_rate_limited_with_its_reset():
    limited = httpx.Response(
        403, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1700000000"}
    )
    client, _ = answer({"/repos/a/b": limited})

    with pytest.raises(RateLimited) as error:
        source(client).full_history("a/b")

    assert error.value.reset_at == datetime.fromtimestamp(1700000000, UTC)


def test_retry_after_is_honoured_before_retrying():
    responses = iter(
        [httpx.Response(429, headers={"retry-after": "7"}), httpx.Response(200, json=REPO)]
    )
    waits = []

    def handler(request):
        if request.url.path.endswith("/history"):
            return httpx.Response(200, json=[week(WEEK_2, 5), week(WEEK_1, 10)])
        return next(responses)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    GitHub(client, sleep=waits.append).full_history("a/b")

    assert 7 in waits


def test_requests_are_spaced_out():
    client, _ = answer(ROUTES)
    waits = []

    GitHub(client, sleep=waits.append, interval=1.0).full_history("a/b")

    assert waits == [1.0]


def test_a_renamed_repo_is_followed_through_its_redirect():
    def handler(request):
        if request.url.path == "/repos/old/b":
            return httpx.Response(301, headers={"location": "https://api.github.com/repos/new/b"})
        return httpx.Response(200, json={"full_name": "new/b", "stargazers_count": 1})

    client = httpx.Client(transport=httpx.MockTransport(handler))

    assert source(client)._get("/repos/old/b")["full_name"] == "new/b"
