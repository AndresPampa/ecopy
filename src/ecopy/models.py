"""Tipos compartidos entre módulos (ver docs/design/etapa-1-tracer-bullet.md)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

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
