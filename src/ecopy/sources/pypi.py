"""Adaptador de PyPI: la primera subida de un paquete que sigue publicada."""

from __future__ import annotations

from datetime import UTC, date, datetime
from urllib.parse import quote

import httpx

from ecopy.sources.clickpy import MalformedResponse, SourceError

_BASE = "https://pypi.org/pypi"


class PyPI:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def first_upload(self, project: str) -> date | None:
        """Día UTC del archivo más viejo que PyPI todavía lista; None si no lista ninguno.

        Las versiones borradas no figuran: por eso un nombre puede tener descargas anteriores.
        """
        try:
            response = self._client.get(f"{_BASE}/{quote(project, safe='')}/json")
        except httpx.HTTPError as error:
            raise SourceError(f"pypi {project}: {error}") from error
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise SourceError(f"pypi {project}: HTTP {response.status_code}")
        try:
            releases = response.json()["releases"]
            uploads = [
                datetime.fromisoformat(item["upload_time_iso_8601"]).astimezone(UTC).date()
                for listed in releases.values()
                for item in listed
            ]
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            raise MalformedResponse(f"pypi {project}: respuesta inesperada") from error
        return min(uploads, default=None)
