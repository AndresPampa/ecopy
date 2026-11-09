"""Tipos compartidos entre módulos (ver docs/design/etapa-1-tracer-bullet.md)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

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


Batch = DownloadBatch | PypiTotalsBatch | PythonMinorBatch


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


class YearTotal(BaseModel):
    model_config = ConfigDict(frozen=True)

    year: int
    downloads: int
    status: PeriodStatus
    coverage: Coverage


class SiteStatus(BaseModel):
    """Estado de la última actualización que muestra el sitio."""

    model_config = ConfigDict(frozen=True)

    last_updated: date | None = None
    """Fecha UTC de la última corrida aceptada."""
    failed: bool = False
    """La última corrida fue rechazada: las cifras son las de la anterior."""

    def __init__(self, last_updated: date | None = None, failed: bool = False) -> None:
        super().__init__(last_updated=last_updated, failed=failed)


class LibraryView(BaseModel):
    """Lo que necesita la ficha de una librería, ya calculado."""

    model_config = ConfigDict(frozen=True)

    project: str
    first_date: date
    last_closed_month: MonthPoint | None
    monthly: tuple[MonthPoint, ...]
    yearly: tuple[YearTotal, ...]
