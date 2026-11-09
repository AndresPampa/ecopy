"""Línea de comandos de ecopy: raíz de composición (ver docs/design/etapa-1-tracer-bullet.md)."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from importlib.metadata import version


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ecopy")
    parser.add_argument("--version", action="version", version=f"ecopy {version('ecopy')}")
    parser.parse_args(argv)
    return 0
