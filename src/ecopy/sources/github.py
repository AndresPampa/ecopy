"""Adaptador de GitHub: historia semanal de estrellas. Solo conteos, nunca identidades."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from ecopy.models import StarWeek
from ecopy.sources.clickpy import SourceError

_BASE = "https://api.github.com"
_PAGE_SIZE = 30
_MAX_PAGES = 100
_RESERVE = 100
"""Consultas que se dejan sin usar de la cuota por hora, solo con token."""
_ATTEMPTS = 4
_SECONDARY_WAIT = 60
_MAX_RETRY_AFTER = 120
"""Una espera más larga corta la corrida: reintentar antes de tiempo arriesga un bloqueo."""


class BudgetExhausted(Exception):
    """Se alcanzó el presupuesto de la corrida o queda poca cuota: se retoma en otra."""


class RateLimited(Exception):
    """GitHub rechazó la consulta por límite de uso."""

    def __init__(self, reset_at: datetime | None) -> None:
        super().__init__(f"límite de GitHub; se libera en {reset_at}")
        self.reset_at = reset_at


@dataclass(frozen=True)
class RepoStars:
    repo: str
    full_name: str
    stars: int
    weeks: tuple[StarWeek, ...]


class GitHub:
    def __init__(
        self,
        client: httpx.Client,
        *,
        token: str | None = None,
        budget: int | None = None,
        sleep: Callable[[float], None] = time.sleep,
        interval: float = 1.0,
        deadline: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """`deadline`: segundos de la corrida; al pasarlos corta con RateLimited."""
        self._client = client
        self._token = token
        self._budget = budget
        self._sleep = sleep
        self._interval = interval
        self._remaining: int | None = None
        self._clock = clock
        self._deadline_at = clock() + deadline if deadline is not None else None
        self.requests = 0

    def full_history(self, repo: str) -> RepoStars:
        """Todas las semanas del repo, verificadas contra su conteo actual."""
        info = self._get(f"/repos/{repo}")
        weeks: list[StarWeek] = []
        for page in range(1, _MAX_PAGES + 1):
            rows = self._page(repo, page)
            weeks.extend(rows)
            if len(rows) < _PAGE_SIZE:
                break
        stars = _count(info, repo)
        total = sum(week.stars for week in weeks)
        if abs(total - stars) > max(5, stars // 1000):
            raise SourceError(f"{repo}: la historia suma {total} y el repo tiene {stars}")
        return _stars(repo, info, stars, weeks)

    def recent(self, repo: str) -> RepoStars:
        """Las últimas 30 semanas y el conteo actual."""
        info = self._get(f"/repos/{repo}")
        return _stars(repo, info, _count(info, repo), self._page(repo, 1))

    def _page(self, repo: str, page: int) -> list[StarWeek]:
        path = f"/repos/{repo}/stargazers/history"
        rows = self._get(path, {"per_page": _PAGE_SIZE, "page": page})
        try:
            return [
                StarWeek(repo, datetime.fromtimestamp(row["week"], UTC).date(), int(row["total"]))
                for row in rows
            ]
        except (KeyError, TypeError, ValueError) as error:
            raise SourceError(f"{repo}: respuesta inesperada de la historia") from error

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ecopy",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _check_allowance(self) -> None:
        if self._budget is not None and self.requests >= self._budget:
            raise BudgetExhausted("presupuesto de la corrida")
        if self._token and self._remaining is not None and self._remaining < _RESERVE:
            raise BudgetExhausted("poca cuota por hora")
        if self._deadline_at is not None and self._clock() >= self._deadline_at:
            raise RateLimited(None)

    def _wait(self, seconds: float) -> None:
        """Duerme, salvo que la espera pase el plazo: así el paso guarda antes de su timeout."""
        if self._deadline_at is not None and self._clock() + seconds > self._deadline_at:
            raise RateLimited(None)
        self._sleep(seconds)

    def _get(self, path: str, params: dict | None = None):
        self._check_allowance()
        if self.requests:
            self._wait(self._interval)
        for attempt in range(_ATTEMPTS):
            try:
                response = self._client.get(
                    _BASE + path, params=params, headers=self._headers(), follow_redirects=True
                )
            except httpx.TransportError as error:
                raise SourceError(f"{path}: {type(error).__name__}") from error
            self.requests += 1
            remaining = response.headers.get("x-ratelimit-remaining")
            self._remaining = int(remaining) if remaining is not None else None
            if response.status_code == 200:
                return response.json()
            if response.status_code not in (403, 429):
                raise SourceError(f"{path}: {response.status_code}")
            self._wait_or_raise(response, attempt)
        raise RateLimited(None)

    def _wait_or_raise(self, response: httpx.Response, attempt: int) -> None:
        retry_after = response.headers.get("retry-after")
        if retry_after is not None:
            try:
                wait = float(retry_after)
            except ValueError:
                raise RateLimited(None) from None
            if not 0 <= wait <= _MAX_RETRY_AFTER:  # también descarta nan e inf
                raise RateLimited(None)
            self._wait(wait)
            return
        if response.headers.get("x-ratelimit-remaining") == "0":
            reset = response.headers.get("x-ratelimit-reset")
            raise RateLimited(datetime.fromtimestamp(int(reset), UTC) if reset else None)
        self._wait(_SECONDARY_WAIT * 2**attempt)


def _count(info: dict, repo: str) -> int:
    try:
        return int(info["stargazers_count"])
    except (KeyError, TypeError, ValueError) as error:
        raise SourceError(f"{repo}: respuesta inesperada del repo") from error


def _stars(repo: str, info: dict, stars: int, weeks: list[StarWeek]) -> RepoStars:
    ordered = tuple(sorted(weeks, key=lambda w: w.week))
    return RepoStars(repo, str(info.get("full_name", repo)), stars, ordered)
