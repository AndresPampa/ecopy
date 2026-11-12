"""Tipos compartidos entre módulos (ver docs/design/etapa-1-tracer-bullet.md)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_SAFE_FILE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

DailySeries = Mapping[date, int]
"""Descargas por día de un paquete, ordenadas por fecha."""


@dataclass(frozen=True)
class DailyDownload:
    project: str
    date: date
    downloads: int


@dataclass(frozen=True)
class DownloadBatch:
    source: Literal["clickpy"]
    rows: tuple[DailyDownload, ...]


@dataclass(frozen=True)
class DailyTotal:
    """Descargas de todo PyPI en un día: el denominador de las cuotas."""

    date: date
    downloads: int


@dataclass(frozen=True)
class PypiTotalsBatch:
    source: Literal["clickpy"]
    rows: tuple[DailyTotal, ...]


@dataclass(frozen=True)
class PythonMinorMonth:
    """Descargas de todo PyPI en un mes por versión de Python, con el valor crudo de la fuente."""

    month: date
    python_minor: str
    downloads: int


@dataclass(frozen=True)
class PythonMinorBatch:
    source: Literal["clickpy"]
    rows: tuple[PythonMinorMonth, ...]


@dataclass(frozen=True)
class StarWeek:
    """Estrellas netas ganadas en una semana calendario (empieza en domingo)."""

    repo: str
    week: date
    stars: int


@dataclass(frozen=True)
class StarWeeksBatch:
    source: Literal["github"]
    rows: tuple[StarWeek, ...]


@dataclass(frozen=True)
class StarTotal:
    """`stargazers_count` de un repo el día de la corrida."""

    repo: str
    date: date
    stars: int


@dataclass(frozen=True)
class StarTotalsBatch:
    source: Literal["github"]
    rows: tuple[StarTotal, ...]


Batch = DownloadBatch | PypiTotalsBatch | PythonMinorBatch | StarWeeksBatch | StarTotalsBatch


@dataclass(frozen=True)
class AppendResult:
    """Qué escribió una corrida: las filas iguales a la versión vigente no se escriben."""

    paths: list[Path]
    new_rows: int
    revised_rows: int


@dataclass(frozen=True)
class Problem:
    """Por qué se rechaza una corrida."""

    code: str
    dataset: str
    detail: str


@dataclass(frozen=True)
class DatasetCounts:
    new_rows: int
    revised_rows: int


@dataclass(frozen=True)
class RunReport:
    """Registro de una ejecución de la ingesta: mide correcciones y alimenta el aviso del sitio."""

    id: str
    captured_at: datetime
    status: Literal["ok", "failed"]
    problems: tuple[Problem, ...]
    datasets: Mapping[str, DatasetCounts]
    last_day: date | None


@dataclass(frozen=True)
class StarsReport:
    """Qué hizo una corrida de estrellas; va aparte para no tocar el estado del sitio."""

    id: str
    captured_at: datetime
    status: Literal["complete", "partial"]
    requests: int
    backfilled: tuple[str, ...]
    updated: tuple[str, ...]
    pending: int
    failed: tuple[tuple[str, str], ...]
    moved: tuple[tuple[str, str], ...]
    stopped: str | None


@dataclass(frozen=True)
class Run:
    """Una corrida de ingesta: la procedencia que el store sella en lo que escribe."""

    id: str
    captured_at: datetime
    acquisition: Literal["backfill", "observed"]

    def __post_init__(self) -> None:
        if not _SAFE_FILE_NAME.fullmatch(self.id):
            raise ValueError(f"id de corrida inválido para un nombre de archivo: {self.id!r}")
        if self.captured_at.utcoffset() is None:
            raise ValueError("captured_at debe tener zona horaria")


PeriodStatus = Literal["complete", "in_progress", "package_start", "source_gap", "degraded"]
"""Estado de un mes o un año, de más a menos urgente: en curso, desde el primer release del
paquete, con huecos de la fuente, con días degradados, completo."""


class Coverage(BaseModel):
    """Días de un período según el calendario de calidad de la fuente."""

    model_config = ConfigDict(frozen=True)

    expected: int
    gap: int
    degraded: int

    @property
    def with_data(self) -> int:
        return self.expected - self.gap


class MonthPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    month: date
    """Primer día del mes."""
    downloads: int | None
    """None = sin datos ese mes (los huecos no se interpolan ni se muestran como cero)."""
    status: PeriodStatus
    coverage: Coverage
    share: float | None = None
    """Fracción de todas las descargas de PyPI de ese mes; None sin datos o sin el total."""


class YearTotal(BaseModel):
    model_config = ConfigDict(frozen=True)

    year: int
    downloads: int
    status: PeriodStatus
    coverage: Coverage


class CategoryShare(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    downloads: int
    share: float
    """Fracción del total del catálogo."""


class DomainShare(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    downloads: int
    share: float
    categories: tuple[CategoryShare, ...]


class Mover(BaseModel):
    model_config = ConfigDict(frozen=True)

    project: str
    category: str
    share: float
    share_change: float
    """Diferencia en puntos de cuota contra el período anterior."""
    rank: int | None
    """Posición entre los paquetes elegibles; None si no tuvo descargas en el período."""
    rank_change: int | None
    """Posiciones ganadas; None si falta alguno de los dos períodos."""


class Newcomer(BaseModel):
    model_config = ConfigDict(frozen=True)

    project: str
    category: str
    rank: int
    """Posición en el top 100 de todo PyPI."""


class VolumeView(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int
    previous: int | None
    growth: float | None
    """None si no hay período anterior o la comparación cruza una discontinuidad."""
    discontinuities: tuple[date, ...]


class PythonVersionShare(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    downloads: int
    share: float
    """Fracción de las descargas con una versión real de CPython."""


class TimelineEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    date: date
    version: str
    kind: Literal["release", "end_of_life"]


class YearView(BaseModel):
    """Todo lo que muestra la página de un año; serializable para congelarlo."""

    model_config = ConfigDict(frozen=True)

    year: int
    status: Literal["closed", "ytd"]
    methodology_version: int
    period_start: date
    period_end: date
    previous_start: date | None
    previous_end: date | None
    coverage: Coverage
    volume: VolumeView
    catalog_share: float
    """Fracción de todo PyPI que representa el catálogo."""
    domains: tuple[DomainShare, ...]
    movers_up: tuple[Mover, ...]
    movers_down: tuple[Mover, ...]
    newcomers: tuple[Newcomer, ...]
    python_versions: tuple[PythonVersionShare, ...]
    python_unknown_share: float
    python_other_share: float
    timeline: tuple[TimelineEvent, ...]
    provisional: bool = Field(default=False, exclude=True)
    """Año cerrado que todavía no se congeló: se calcula en cada build y no se guarda."""


class SiteStatus(BaseModel):
    """Estado de la última actualización que muestra el sitio."""

    model_config = ConfigDict(frozen=True)

    last_updated: date | None = None
    """Fecha UTC de la última corrida aceptada."""
    failed: bool = False
    """La última corrida fue rechazada: las cifras son las de la anterior."""

    def __init__(self, last_updated: date | None = None, failed: bool = False) -> None:
        super().__init__(last_updated=last_updated, failed=failed)


class StarPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    week: date
    stars: int
    """Estrellas netas acumuladas hasta esa semana."""


class StarsView(BaseModel):
    model_config = ConfigDict(frozen=True)

    repo: str
    total: int
    points: tuple[StarPoint, ...]
    shared_with: tuple[str, ...]
    """Otros paquetes del catálogo que publican desde el mismo repo."""


class LibraryView(BaseModel):
    """Lo que necesita la ficha de una librería, ya calculado."""

    model_config = ConfigDict(frozen=True)

    project: str
    first_date: date
    earlier_downloads: int = 0
    """Descargas que el nombre tuvo antes de su primera versión vigente; no entran en la serie."""
    last_closed_month: MonthPoint | None
    monthly: tuple[MonthPoint, ...]
    yearly: tuple[YearTotal, ...]
    discontinuities: tuple[date, ...] = ()
    """Cambios de nivel de la fuente dentro de la historia del paquete."""
    category: str | None = None
    domain: str | None = None
    tags: tuple[str, ...] = ()
    repo: str | None = None
    renamed_from: str | None = None
    renamed_to: str | None = None
    stars: StarsView | None = None


class LibraryRow(BaseModel):
    """Una fila de los listados."""

    model_config = ConfigDict(frozen=True)

    project: str
    category: str
    domain: str
    tags: tuple[str, ...]
    month: date | None
    downloads: int | None
    """Del último mes cerrado con datos."""
    trend: tuple[float, ...]
    """Cuota de PyPI de los últimos meses cerrados, de la más vieja a la más nueva."""


class YearShare(BaseModel):
    model_config = ConfigDict(frozen=True)

    year: int
    status: Literal["closed", "ytd"]
    share: float


class CategoryPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    domain: str
    shares: tuple[YearShare, ...]
    rows: tuple[LibraryRow, ...]


class DomainPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    shares: tuple[YearShare, ...]
    categories: tuple[CategoryPage, ...]


class ReleaseRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    released: date
    end_of_life: date | None
    status: Literal["supported", "end_of_life", "unknown"]


class ReleasesView(BaseModel):
    model_config = ConfigDict(frozen=True)

    as_of: date
    releases: tuple[ReleaseRow, ...]


class BrowseView(BaseModel):
    """Lo que necesitan el catálogo, los dominios, el comparador y los releases."""

    model_config = ConfigDict(frozen=True)

    rows: tuple[LibraryRow, ...]
    domains: tuple[DomainPage, ...]
    releases: ReleasesView
    tags: tuple[str, ...]
