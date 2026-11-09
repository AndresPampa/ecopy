"""Tipos compartidos entre módulos (ver docs/design/etapa-1-tracer-bullet.md)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
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


class MonthPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    month: date
    """Primer día del mes."""
    downloads: int | None
    """None = sin datos ese mes (los huecos no se interpolan ni se muestran como cero)."""
    partial: bool
    """El mes está en curso a la fecha `as_of`."""


class YearTotal(BaseModel):
    model_config = ConfigDict(frozen=True)

    year: int
    downloads: int
    partial: bool
    """Año con cobertura incompleta en la fuente (2016 empieza el 22-ene y tiene huecos)."""
    ytd: bool
    """Año en curso a la fecha `as_of`: acumulado parcial, no comparable con un año cerrado."""


class LibraryView(BaseModel):
    """Lo que necesita la ficha de una librería, ya calculado."""

    model_config = ConfigDict(frozen=True)

    project: str
    first_date: date
    last_closed_month: MonthPoint | None
    monthly: tuple[MonthPoint, ...]
    yearly: tuple[YearTotal, ...]
