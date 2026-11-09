"""Graba respuestas reales de ClickPy para los tests de contrato (requiere red).

Uso:  uv run python tests/fixtures/clickpy/record.py

Corre el adaptador real con un transport que guarda, por etiqueta de consulta, el cuerpo y el
resumen. Volver a correrlo cuando cambien las consultas del adaptador.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import httpx

from ecopy.sources.clickpy import ClickPy

TAG = re.compile(r"/\* ecopy:(\w+) \*/")


class Recording(httpx.BaseTransport):
    def __init__(self) -> None:
        self._inner = httpx.HTTPTransport()
        self.exchanges: dict[str, dict] = {}

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = self._inner.handle_request(request)
        response.read()
        tag = TAG.search(request.content.decode()).group(1)
        self.exchanges[tag] = {
            "summary": json.loads(response.headers["X-ClickHouse-Summary"]),
            "body": response.text,
        }
        return response


def main() -> None:
    transport = Recording()
    with httpx.Client(transport=transport, timeout=120) as client:
        ClickPy(client).daily_downloads(["fastapi"], date(2024, 1, 1), date(2024, 1, 31))
    out = Path(__file__).parent / "fastapi_2024-01.json"
    out.write_text(json.dumps(transport.exchanges, indent=1) + "\n")
    print(f"{out}: {sorted(transport.exchanges)}")


if __name__ == "__main__":
    main()
