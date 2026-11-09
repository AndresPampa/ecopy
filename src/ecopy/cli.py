"""Línea de comandos de ecopy: raíz de composición (ver docs/design/etapa-1-tracer-bullet.md)."""

from __future__ import annotations

import argparse
import contextlib
import functools
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
from pathlib import Path
from typing import Literal

import httpx

from ecopy.metrics import library_view
from ecopy.models import Run
from ecopy.site import render_site
from ecopy.sources.clickpy import ClickPy, SourceError
from ecopy.store import ImmutabilityError, Store

BACKFILL_START = date(2016, 1, 22)  # primer día con datos en ClickPy (spike S1)


@dataclass(frozen=True)
class IngestWindow:
    start: date
    end: date
    acquisition: Literal["backfill", "observed"]


def ingest_window(last_saved: date | None, since: date, now: datetime) -> IngestWindow | None:
    """Qué pedir a la fuente; None si ya está al día.

    Termina ayer (UTC) porque el día en curso está incompleto en la fuente (spike S1).
    """
    end = now.astimezone(UTC).date() - timedelta(days=1)
    if last_saved is None:
        return IngestWindow(since, end, "backfill") if since <= end else None
    if last_saved >= end:
        return None
    return IngestWindow(last_saved + timedelta(days=1), end, "observed")


def make_server(out: Path, port: int) -> ThreadingHTTPServer:
    """Servidor local del sitio que aplica `_headers`, para probar la CSP real."""
    headers = _parse_headers((Path(out) / "_headers").read_text(encoding="utf-8"))

    class Handler(SimpleHTTPRequestHandler):
        def end_headers(self) -> None:
            for name, value in headers:
                self.send_header(name, value)
            super().end_headers()

    handler = functools.partial(Handler, directory=str(out))
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


def _parse_headers(text: str) -> list[tuple[str, str]]:
    pairs = (line.strip().split(": ", 1) for line in text.splitlines() if line.startswith("  "))
    return [(name, value) for name, value in pairs]


def _ingest(args: argparse.Namespace, http: httpx.Client | None, now: datetime) -> int:
    store = Store(args.data)
    saved = store.daily_downloads([args.project]).get(args.project, {})
    window = ingest_window(max(saved, default=None), args.since, now)
    if window is None:
        print(f"{args.project}: ya está al día")
        return 0
    client = http or httpx.Client(timeout=120)
    try:
        batch = ClickPy(client).daily_downloads([args.project], window.start, window.end)
    finally:
        if http is None:
            client.close()
    if not batch.rows:
        print(f"{args.project}: sin datos nuevos entre {window.start} y {window.end}")
        return 0 if saved else 1
    run_id = f"{now.astimezone(UTC):%Y%m%dT%H%M%SZ}-{window.acquisition}"
    paths = store.append(batch, Run(run_id, now, window.acquisition))
    print(f"{args.project}: {len(batch.rows)} días ({window.acquisition}) en {len(paths)} archivos")
    return 0


def _build(args: argparse.Namespace) -> int:
    series = Store(args.data).daily_downloads([args.project]).get(args.project)
    if not series:
        print(f"ecopy: {args.project} no tiene datos; correr `ecopy ingest`", file=sys.stderr)
        return 1
    # La página refleja hasta donde llegan los datos, sin depender del reloj.
    render_site([library_view(args.project, series, as_of=max(series))], args.out)
    print(f"sitio en {args.out}: /en/library/{args.project}/ y /es/library/{args.project}/")
    return 0


def _serve(args: argparse.Namespace) -> int:
    with make_server(args.out, args.port) as server:
        print(f"http://127.0.0.1:{server.server_address[1]}/en/library/ (Ctrl+C para salir)")
        with contextlib.suppress(KeyboardInterrupt):
            server.serve_forever()
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ecopy")
    parser.add_argument("--version", action="version", version=f"ecopy {version('ecopy')}")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest = commands.add_parser("ingest", help="trae descargas de ClickPy al store")
    ingest.add_argument("--project", required=True)
    ingest.add_argument("--since", type=date.fromisoformat, default=BACKFILL_START)
    ingest.add_argument("--data", type=Path, default=Path("data"))

    build = commands.add_parser("build", help="genera el sitio estático")
    build.add_argument("--project", required=True)
    build.add_argument("--data", type=Path, default=Path("data"))
    build.add_argument("--out", type=Path, default=Path("build/site"))

    serve = commands.add_parser("serve", help="sirve el sitio en localhost con su CSP")
    serve.add_argument("--out", type=Path, default=Path("build/site"))
    serve.add_argument("--port", type=int, default=8000)
    return parser


def _utcnow() -> datetime:
    return datetime.now(UTC)


def main(
    argv: Sequence[str] | None = None,
    *,
    http: httpx.Client | None = None,
    now: Callable[[], datetime] = _utcnow,
) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "ingest":
            return _ingest(args, http, now())
        if args.command == "build":
            return _build(args)
        return _serve(args)
    except (SourceError, ImmutabilityError, FileNotFoundError) as error:
        print(f"ecopy: {error}", file=sys.stderr)
        return 1
