"""Línea de comandos de ecopy: parser y raíz de composición (`docs/design/etapa-2-*.md`)."""

from __future__ import annotations

import argparse
import contextlib
import functools
import sys
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
from pathlib import Path

import httpx

from ecopy.catalog import Catalog, CatalogError, refresh_top100
from ecopy.metrics import library_view, site_status
from ecopy.models import Problem
from ecopy.pipeline import REOBSERVE_DAYS, ingest, validate_store
from ecopy.site import render_site
from ecopy.sources.clickpy import ClickPy, SourceError
from ecopy.store import ImmutabilityError, Store


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


@contextlib.contextmanager
def _client(http: httpx.Client | None) -> Iterator[httpx.Client]:
    """El cliente inyectado no se cierra: es de quien lo creó."""
    if http is not None:
        yield http
        return
    with httpx.Client(timeout=180) as client:
        yield client


def _projects(args: argparse.Namespace) -> Sequence[str]:
    return args.project or Catalog.load(args.catalog).projects


def _print_problems(problems: Sequence[Problem]) -> None:
    for problem in problems:
        print(f"ecopy: [{problem.code}] {problem.dataset} {problem.detail}", file=sys.stderr)


def _ingest(args: argparse.Namespace, http: httpx.Client | None, now: datetime) -> int:
    projects = _projects(args)
    with _client(http) as client:
        report = ingest(
            projects, ClickPy(client), Store(args.data), now=now, reobserve_days=args.reobserve_days
        )
    if report.status == "failed":
        _print_problems(report.problems)
        return 1
    for name, counts in report.datasets.items():
        print(f"{name}: {counts.new_rows} filas nuevas, {counts.revised_rows} corregidas")
    print(f"datos hasta {report.last_day}")
    return 0


def _validate(args: argparse.Namespace, now: datetime) -> int:
    problems = validate_store(_projects(args), Store(args.data), now=now)
    _print_problems(problems)
    if not problems:
        print("sin problemas")
    return 1 if problems else 0


def _build(args: argparse.Namespace) -> int:
    projects = _projects(args)
    store = Store(args.data)
    series = store.daily_downloads(projects)
    if not series:
        print("ecopy: no hay datos para construir; correr `ecopy ingest`", file=sys.stderr)
        return 1
    for project in sorted(set(projects) - set(series)):
        print(f"ecopy: {project} no tiene datos; se omite", file=sys.stderr)
    # El mismo `as_of` para todos: un paquete sin descargas recientes no cierra antes su historia.
    as_of = max(max(days) for days in series.values())
    pages = [library_view(project, days, as_of=as_of) for project, days in sorted(series.items())]
    render_site(pages, args.out, status=site_status(store.runs()))
    print(f"sitio en {args.out}: {len(pages)} fichas en /en/library/ y /es/library/")
    return 0


def _catalog(args: argparse.Namespace, http: httpx.Client | None, now: datetime) -> int:
    with _client(http) as client:
        source = ClickPy(client)
        if args.action == "refresh":
            added = refresh_top100(args.catalog, source, now=now)
            print(f"top 100 actualizado; {len(added)} paquetes nuevos")
            for project in added:
                print(project)
            return 0
        projects = Catalog.load(args.catalog).projects
        missing = sorted(set(projects) - source.known_projects(projects))
    for project in missing:
        print(f"ecopy: {project} no tiene datos en ClickPy", file=sys.stderr)
    if not missing:
        print(f"{len(projects)} paquetes con datos en la fuente")
    return 1 if missing else 0


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

    def data_options(command: argparse.ArgumentParser) -> None:
        command.add_argument("--project", action="append", help="por defecto, todo el catálogo")
        command.add_argument("--catalog", type=Path, default=Path("catalog"))
        command.add_argument("--data", type=Path, default=Path("data"))

    ingest_command = commands.add_parser("ingest", help="trae datos de ClickPy al store")
    data_options(ingest_command)
    ingest_command.add_argument("--reobserve-days", type=int, default=REOBSERVE_DAYS)

    data_options(commands.add_parser("validate", help="revisa los últimos días guardados"))

    build = commands.add_parser("build", help="genera el sitio estático")
    data_options(build)
    build.add_argument("--out", type=Path, default=Path("build/site"))

    catalog = commands.add_parser("catalog", help="mantiene el catálogo")
    catalog.add_argument("action", choices=["refresh", "check"])
    catalog.add_argument("--catalog", type=Path, default=Path("catalog"))

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
        if args.command == "validate":
            return _validate(args, now())
        if args.command == "build":
            return _build(args)
        if args.command == "catalog":
            return _catalog(args, http, now())
        return _serve(args)
    except (SourceError, ImmutabilityError, CatalogError, FileNotFoundError) as error:
        print(f"ecopy: {error}", file=sys.stderr)
        return 1
