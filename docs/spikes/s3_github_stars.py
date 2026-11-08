# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]
# ///
"""Spike S3 — Fuente del histórico de estrellas de GitHub.

Uso:  uv run docs/spikes/s3_github_stars.py

Sin token (60 consultas/hora por IP): usa ~12. Si existe la variable de entorno GITHUB_TOKEN se
envía como cabecera (nunca se imprime). Solo lee conteos: no toca ni guarda identidades de
usuarios. Respalda docs/spikes/s3-github-estrellas.md.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import httpx

API = "https://api.github.com"
FULL = "astral-sh/uv"      # repo joven: historia completa en pocas páginas
OLD = "psf/requests"       # repo viejo: solo primera y última página


def client() -> httpx.Client:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "ecopy-spike",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(base_url=API, headers=headers, timeout=60, follow_redirects=True)


def day(ts: int) -> str:
    return datetime.fromtimestamp(ts, UTC).date().isoformat()


def history(c: httpx.Client, repo: str) -> tuple[list[dict], int]:
    """Todas las semanas de estrellas del repo (más reciente primero) y páginas usadas."""
    weeks, url, pages = [], f"/repos/{repo}/stargazers/history", 0
    while url:
        r = c.get(url)
        r.raise_for_status()
        weeks += r.json()
        pages += 1
        url = r.links.get("next", {}).get("url")
    return weeks, pages


def main() -> None:
    with client() as c:
        print("## 1. Endpoint de historia (primera página de", OLD + ")")
        r = c.get(f"/repos/{OLD}/stargazers/history")
        r.raise_for_status()
        first = r.json()
        last_page = r.links["last"]["url"]
        print(f"status {r.status_code} · semanas por página {len(first)} · última página {last_page}")
        print("forma de un elemento:", first[0])

        print("\n## 2. Semana más antigua de", OLD)
        old = c.get(last_page).json()
        oldest = min(old, key=lambda w: w["week"])
        meta_old = c.get(f"/repos/{OLD}").json()
        print(f"semana {day(oldest['week'])} total {oldest['total']} · repo creado {meta_old['created_at']}")

        print("\n## 3. Historia completa de", FULL, "vs stargazers_count")
        weeks, pages = history(c, FULL)
        meta = c.get(f"/repos/{FULL}").json()
        total = sum(w["total"] for w in weeks)
        by_days = sum(sum(w["days"]) for w in weeks)
        negatives = sum(1 for w in weeks for d in w["days"] if d < 0)
        print(f"páginas {pages} · semanas {len(weeks)} · {day(min(w['week'] for w in weeks))} → "
              f"{day(max(w['week'] for w in weeks))}")
        print(f"suma semanas {total} · suma días {by_days} · stargazers_count "
              f"{meta['stargazers_count']} · días negativos {negatives}")

        print("\n## 4. Alternativa: listado de stargazers con starred_at")
        r = c.get(f"/repos/{OLD}/stargazers", params={"per_page": 1},
                  headers={"Accept": "application/vnd.github.star+json"})
        print(f"status {r.status_code} · {r.json().get('message', 'ok') if r.is_error else 'ok'}")

        r = c.get("/rate_limit")
        core = r.json()["resources"]["core"]
        print(f"\n## Cuota restante: {core['remaining']}/{core['limit']}")


if __name__ == "__main__":
    main()
