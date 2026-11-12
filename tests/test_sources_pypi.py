"""Adaptador de PyPI: primera subida que sigue publicada de un paquete."""

from datetime import date

import httpx
import pytest

from ecopy.sources.clickpy import SourceError
from ecopy.sources.pypi import PyPI


def client(answers: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        body = answers[request.url.path]
        return body if isinstance(body, httpx.Response) else httpx.Response(200, json=body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def files(*times: str) -> list[dict]:
    return [{"upload_time_iso_8601": time} for time in times]


OPENAI = {
    "releases": {
        "0.1.0": files("2020-06-13T03:16:42.123456Z"),
        "0.0.2": files("2020-02-18T19:41:36.000000Z", "2020-02-18T19:41:40.000000Z"),
        "9.9.9": [],
    }
}


def test_the_first_upload_is_the_oldest_file_still_published():
    pypi = PyPI(client({"/pypi/openai/json": OPENAI}))

    assert pypi.first_upload("openai") == date(2020, 2, 18)


def test_the_day_is_taken_in_utc():
    late = {"releases": {"1": files("2020-02-18T23:30:00.000000-05:00")}}

    assert PyPI(client({"/pypi/x/json": late})).first_upload("x") == date(2020, 2, 19)


def test_a_project_without_files_or_unknown_to_pypi_has_no_first_upload():
    answers = {"/pypi/empty/json": {"releases": {"1": []}}, "/pypi/gone/json": httpx.Response(404)}
    pypi = PyPI(client(answers))

    assert pypi.first_upload("empty") is None
    assert pypi.first_upload("gone") is None


@pytest.mark.parametrize(
    "body",
    [
        httpx.Response(503),
        httpx.Response(500, json={"releases": {}}),
        httpx.Response(200, text="<html>"),
        {"info": {}},
        {"releases": {"1": [{"upload_time_iso_8601": "ayer"}]}},
        {"releases": {"1": [{}]}},
        {"releases": []},
    ],
)
def test_an_error_or_an_unexpected_body_is_a_source_error(body):
    with pytest.raises(SourceError):
        PyPI(client({"/pypi/x/json": body})).first_upload("x")
