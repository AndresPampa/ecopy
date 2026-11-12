"""Línea de comandos de ecopy: parser y raíz de composición (`docs/design/etapa-2-*.md`)."""

from __future__ import annotations

import argparse
import contextlib
import functools
import os
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, date, datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
from pathlib import Path

import httpx

from ecopy.catalog import (
    FIRST_RANKED_YEAR,
    Catalog,
    CatalogError,
    refresh_series_start,
    refresh_top100,
)
from ecopy.metrics import (
    METHODOLOGY_VERSION,
    YearInputs,
    library_rows,
    library_view,
    releases_view,
    site_status,
    stars_view,
    taxonomy_view,
    year_view,
)
from ecopy.models import BrowseView, DailySeries, Problem, StarsView, YearView
from ecopy.pipeline import REOBSERVE_DAYS, ingest, ingest_stars, validate_store
from ecopy.site import render_site
from ecopy.sources.clickpy import ClickPy, SourceError
from ecopy.sources.github import GitHub
from ecopy.sources.pypi import PyPI
from ecopy.store import ImmutabilityError, Store


def make_server(out: Path, port: int) -> ThreadingHTTPServer:
    """Servidor local del sitio que aplica `_headers`, para probar la CSP real."""
    headers = _parse_headers((Path(out) / "_headers").read_text(encoding="utf-8"))

    root = Path(out)
    # Como Pages: la 404 del directorio de idioma pedido, o la de la raíz. Solo nombres que
    # existen en el sitio: un segmento como ".." nunca arma una ruta.
    localized = {page.parent.name: page for page in root.glob("*/404.html")}

    class Handler(SimpleHTTPRequestHandler):
        def end_headers(self) -> None:
            for name, value in headers:
                self.send_header(name, value)
            super().end_headers()

        def send_error(self, code: int, message: str | None = None, explain: str | None = None):
            segment = self.path.split("?", 1)[0].strip("/").split("/", 1)[0]
            page = localized.get(segment, root / "404.html")
            if code != HTTPStatus.NOT_FOUND or not page.is_file():
                super().send_error(code, message, explain)
                return
            body = page.read_bytes()
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

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


class FrozenYearMissing(Exception):
    """Un año cerrado no tiene su vista congelada."""


def _closed_years(totals: DailySeries, as_of: date) -> list[int]:
    years = {day.year for day in totals if day.year >= FIRST_RANKED_YEAR}
    return sorted(year for year in years if date(year, 12, 31) <= as_of)


def _year_views(store: Store, catalog: Catalog, series: dict, as_of: date) -> list[YearView]:
    """Años cerrados desde lo congelado; el año en curso, recalculado."""
    totals = store.pypi_daily_totals()
    views = []
    for year in _closed_years(totals, as_of):
        view = store.frozen_year(year)
        if view is None:
            raise FrozenYearMissing(f"{year} no está congelado; correr `ecopy freeze`")
        views.append(view)
    if as_of.year >= FIRST_RANKED_YEAR and date(as_of.year, 12, 31) > as_of:
        inputs = YearInputs(series, totals, store.python_minor_monthly(), catalog)
        views.append(year_view(as_of.year, inputs, as_of=as_of))
    return views


def _library_stars(store: Store, catalog: Catalog) -> dict[str, StarsView]:
    """Vista de estrellas por paquete; un repo compartido aparece en todos sus paquetes."""
    repos = catalog.repos()
    weeks, counts = store.star_weeks(repos), store.star_totals(repos)
    views = {}
    for repo, history in weeks.items():
        projects = catalog.projects_of_repo(repo)
        for project in projects:
            others = tuple(p for p in projects if p != project)
            views[project] = stars_view(repo, history, counts.get(repo, {}), shared_with=others)
    return views


def _browse(pages, years, catalog: Catalog, as_of: date) -> BrowseView:
    rows = library_rows(pages)
    return BrowseView(
        rows=rows,
        domains=taxonomy_view(years, rows, catalog),
        releases=releases_view(catalog.python_releases(), as_of=as_of),
        tags=catalog.tags(),
    )


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
    # Las cuotas solo tienen sentido con todo el catálogo.
    catalog = None if args.project else Catalog.load(args.catalog)
    years = _year_views(store, catalog, series, as_of) if catalog else []
    totals = store.pypi_daily_totals()
    stars = _library_stars(store, catalog) if catalog else {}
    pages = [
        library_view(
            project,
            days,
            as_of=as_of,
            totals=totals,
            catalog=catalog,
            stars=stars.get(project),
        )
        for project, days in sorted(series.items())
    ]
    labels = catalog.labels() if catalog else {}
    browse = _browse(pages, years, catalog, as_of) if catalog else None
    render_site(
        pages,
        args.out,
        status=site_status(store.runs()),
        years=years,
        labels=labels,
        browse=browse,
    )
    print(f"sitio en {args.out}: {len(pages)} fichas y {len(years)} años")
    return 0


def _freeze(args: argparse.Namespace) -> int:
    catalog = Catalog.load(args.catalog)
    store = Store(args.data)
    totals = store.pypi_daily_totals()
    if not totals:
        print("ecopy: no hay datos para congelar; correr `ecopy ingest`", file=sys.stderr)
        return 1
    as_of = max(totals)
    pending = []
    for year in _closed_years(totals, as_of):
        frozen = store.frozen_year(year)
        if frozen is None or frozen.methodology_version < METHODOLOGY_VERSION:
            pending.append(year)
    missing = [year for year in pending if not catalog.top(year)]
    if missing:
        print(
            f"ecopy: falta el top 100 de {missing}; correr `ecopy catalog refresh`", file=sys.stderr
        )
        return 1
    if pending:
        series = store.daily_downloads(catalog.projects)
        inputs = YearInputs(series, totals, store.python_minor_monthly(), catalog)
        for year in pending:
            store.freeze_year(year_view(year, inputs, as_of=as_of))
    print(f"{len(pending)} años congelados: {pending}")
    return 0


def _catalog(args: argparse.Namespace, http: httpx.Client | None, now: datetime) -> int:
    with _client(http) as client:
        if args.action == "starts":
            projects = Catalog.load(args.catalog).projects
            series = Store(args.data).daily_downloads(projects)
            starts = refresh_series_start(args.catalog, PyPI(client), series)
            print(f"{len(starts)} series con inicio recortado")
            for project, day in starts.items():
                print(f"{project}\t{day}")
            return 0
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


_MAX_WITHOUT_TOKEN = 50


def _stars(
    args: argparse.Namespace,
    http: httpx.Client | None,
    now: datetime,
    sleep: Callable[[float], None],
) -> int:
    catalog = Catalog.load(args.catalog)
    known = catalog.repos()
    unknown = sorted(set(args.repo or ()) - set(known))
    if unknown:
        print(f"ecopy: repos fuera del catálogo: {', '.join(unknown)}", file=sys.stderr)
        return 1
    token = os.environ.get("GITHUB_TOKEN") or None
    budget = args.budget
    if token is None:
        budget = min(budget, _MAX_WITHOUT_TOKEN)
        print(
            f"ecopy: sin GITHUB_TOKEN; máximo {_MAX_WITHOUT_TOKEN} consultas en esta corrida",
            file=sys.stderr,
        )
    with _client(http) as client:
        source = GitHub(
            client, token=token, budget=budget, sleep=sleep, deadline=args.max_minutes * 60
        )
        report = ingest_stars(args.repo or known, source, Store(args.data), now=now)
    print(
        f"{len(report.backfilled)} con historia completa, {len(report.updated)} actualizados, "
        f"{report.pending} pendientes, {report.requests} consultas"
    )
    if report.stopped:
        print(f"la corrida se detuvo ({report.stopped}): volver a correr para seguir")
    for repo, new in report.moved:
        print(f"ecopy: {repo} ahora es {new}; corregir catalog/repos.yaml", file=sys.stderr)
    for repo, detail in report.failed:
        print(f"ecopy: {repo} falló: {detail}", file=sys.stderr)
    return 0


def _serve(args: argparse.Namespace) -> int:
    with make_server(args.out, args.port) as server:
        print(f"http://127.0.0.1:{server.server_address[1]}/en/ (Ctrl+C para salir)")
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

    freeze = commands.add_parser("freeze", help="congela los años cerrados que falten")
    freeze.add_argument("--catalog", type=Path, default=Path("catalog"))
    freeze.add_argument("--data", type=Path, default=Path("data"))

    stars = commands.add_parser("stars", help="trae la historia de estrellas de GitHub")
    stars.add_argument("--catalog", type=Path, default=Path("catalog"))
    stars.add_argument("--data", type=Path, default=Path("data"))
    stars.add_argument("--budget", type=int, default=4000, help="consultas máximas de la corrida")
    stars.add_argument("--repo", action="append", help="por defecto, todos los del catálogo")
    stars.add_argument(
        "--max-minutes",
        type=float,
        default=25,
        help="al pasarlos se detiene y guarda; menor que el timeout del paso en Actions",
    )

    catalog = commands.add_parser("catalog", help="mantiene el catálogo")
    catalog.add_argument("action", choices=["refresh", "check", "starts"])
    catalog.add_argument("--catalog", type=Path, default=Path("catalog"))
    catalog.add_argument("--data", type=Path, default=Path("data"), help="solo para `starts`")

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
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "ingest":
            return _ingest(args, http, now())
        if args.command == "validate":
            return _validate(args, now())
        if args.command == "build":
            return _build(args)
        if args.command == "freeze":
            return _freeze(args)
        if args.command == "stars":
            return _stars(args, http, now(), sleep)
        if args.command == "catalog":
            return _catalog(args, http, now())
        return _serve(args)
    except (
        SourceError,
        ImmutabilityError,
        CatalogError,
        FrozenYearMissing,
        FileNotFoundError,
    ) as error:
        print(f"ecopy: {error}", file=sys.stderr)
        return 1
