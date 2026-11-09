"""Tipos compartidos entre módulos (ver docs/design/etapa-1-tracer-bullet.md)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal


@dataclass(frozen=True)
class DailyDownload:
    project: str
    date: date
    downloads: int


@dataclass(frozen=True)
class DownloadBatch:
    source: Literal["clickpy"]
    rows: tuple[DailyDownload, ...]
