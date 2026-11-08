# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "brotli>=1.1"]
# ///
"""Spike S4 — ECharts vs Plotly: prototipo de ranking + ficha con datos reales.

Uso:  uv run docs/spikes/s4_charts_prototype.py [directorio_salida]   (por defecto build/spikes/s4)

1. Trae de ClickPy (usuario `play`, con control de truncado) el top 15 de 2025 y la serie mensual
   de `fastapi`.
2. Descarga cada librería en una versión fija y mide su peso crudo, gzip y brotli.
3. Genera una página por librería y build (ranking + ficha) servida con una CSP estricta:
   sin scripts ni estilos inline, todo desde 'self'. Un `probe.js` registra violaciones de CSP y
   errores en el DOM para leerlos con Chrome headless.
4. Sirve las páginas en localhost, las abre con Chrome headless, imprime estado y violaciones y
   guarda una captura de cada una.

Las páginas y capturas quedan en el directorio de salida (no se versiona).
"""

from __future__ import annotations

import brotli
import functools
import gzip
import http.server
import json
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import httpx

CLICKPY = "https://sql-clickhouse.clickhouse.com/"
MAX_RESULT_ROWS = 1000
CHROME = shutil.which("google-chrome") or shutil.which("chromium")

LIBS = {
    # nombre: (url pinneada, archivo local, motor)
    "echarts-full": ("https://cdn.jsdelivr.net/npm/echarts@6.1.0/dist/echarts.min.js", "echarts"),
    "echarts-common": ("https://cdn.jsdelivr.net/npm/echarts@6.1.0/dist/echarts.common.min.js", "echarts"),
    "echarts-simple": ("https://cdn.jsdelivr.net/npm/echarts@6.1.0/dist/echarts.simple.min.js", "echarts"),
    "plotly-full": ("https://cdn.jsdelivr.net/npm/plotly.js-dist-min@4.1.2/plotly.min.js", "plotly"),
    "plotly-basic": ("https://cdn.jsdelivr.net/npm/plotly.js-basic-dist-min@4.1.2/plotly-basic.min.js", "plotly"),
}

# Con CSP estricta Plotly no puede inyectar su <style>; publica esta hoja para enlazarla aparte.
PLOTLY_CSS = "https://cdn.jsdelivr.net/npm/plotly.js@4.1.2/dist/plotly.css"

CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "connect-src 'self'; font-src 'self'")

# Se carga antes que la librería: registra violaciones de CSP y errores.
PROBE_JS = """
window.__violations = [];
document.addEventListener('securitypolicyviolation', e => {
  window.__violations.push(e.violatedDirective + ' ← ' + (e.blockedURI || 'inline') +
    (e.sourceFile ? ' @' + e.sourceFile.split('/').pop() + ':' + e.lineNumber : ''));
  document.documentElement.dataset.violations = JSON.stringify(window.__violations);
});
window.addEventListener('error', e => {
  document.documentElement.dataset.error = String(e.message);
});
"""

ECHARTS_INIT = """
const data = JSON.parse(document.getElementById('data').textContent);
const fmt = new Intl.NumberFormat('es', {notation: 'compact', maximumFractionDigits: 1});
const opts = {renderer: 'svg'};
const r = echarts.init(document.getElementById('ranking'), null, opts);
r.setOption({
  title: {text: 'Top 15 descargas 2025'},
  tooltip: {trigger: 'axis', valueFormatter: v => fmt.format(v)},
  grid: {left: 8, right: 24, containLabel: true},
  xAxis: {type: 'value', axisLabel: {formatter: v => fmt.format(v)}},
  yAxis: {type: 'category', inverse: true, data: data.ranking.map(d => d[0])},
  series: [{type: 'bar', data: data.ranking.map(d => d[1])}],
});
const f = echarts.init(document.getElementById('ficha'), null, opts);
f.setOption({
  title: {text: 'fastapi — descargas mensuales'},
  tooltip: {trigger: 'axis', valueFormatter: v => fmt.format(v)},
  grid: {left: 8, right: 24, containLabel: true},
  xAxis: {type: 'time'},
  yAxis: {type: 'value', axisLabel: {formatter: v => fmt.format(v)}},
  dataZoom: [{type: 'slider'}, {type: 'inside'}],
  series: [{type: 'line', showSymbol: false, data: data.ficha}],
});
// getOption() conserva opciones de componentes no incluidos en el build: se mira el modelo.
const missing = ['title', 'dataZoom', 'tooltip'].filter(c => !f.getModel().getComponent(c));
document.documentElement.dataset.status = missing.length ? 'parcial: falta ' + missing.join(', ') : 'ok';
window.addEventListener('resize', () => { r.resize(); f.resize(); });
"""

PLOTLY_INIT = """
const data = JSON.parse(document.getElementById('data').textContent);
const config = {responsive: true, displaylogo: false, locale: 'es'};
const base = {margin: {l: 120, r: 24, t: 40, b: 40}, separators: ',.'};
Promise.all([
  Plotly.newPlot('ranking', [{type: 'bar', orientation: 'h',
      x: data.ranking.map(d => d[1]), y: data.ranking.map(d => d[0])}],
    {...base, title: {text: 'Top 15 descargas 2025'}, yaxis: {autorange: 'reversed'}}, config),
  Plotly.newPlot('ficha', [{type: 'scatter', mode: 'lines',
      x: data.ficha.map(d => d[0]), y: data.ficha.map(d => d[1])}],
    {...base, margin: {...base.margin, l: 60}, title: {text: 'fastapi — descargas mensuales'},
     xaxis: {rangeslider: {visible: true}}}, config),
]).then(() => { document.documentElement.dataset.status = 'ok'; })
  .catch(e => { document.documentElement.dataset.error = String(e); });
"""

PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{csp}">
<title>S4 {name}</title><link rel="stylesheet" href="page.css">{extra_css}
<script src="probe.js"></script><script src="{lib}"></script>
</head><body>
<h1>{name}</h1>
<div id="ranking" class="chart"></div><div id="ficha" class="chart"></div>
<script id="data" type="application/json">{data}</script>
<script src="{init}"></script>
</body></html>
"""

PAGE_CSS = "body{font-family:system-ui,sans-serif;margin:16px}.chart{width:100%;height:420px}"


def clickpy(client: httpx.Client, sql: str) -> list[list[str]]:
    resp = client.post(CLICKPY, params={"user": "play"}, content=f"{sql} FORMAT TSV")
    if resp.is_error:
        raise SystemExit(f"ClickHouse {resp.status_code}: {resp.text[:300]}")
    s = json.loads(resp.headers["X-ClickHouse-Summary"])
    rows = [line.split("\t") for line in resp.text.splitlines()]
    if int(s["read_rows"]) < int(s["total_rows_to_read"]) or len(rows) >= MAX_RESULT_ROWS:
        raise SystemExit("Resultado parcial de ClickPy: partir o paginar la consulta.")
    return rows


def fetch_data(client: httpx.Client) -> dict:
    ranking = clickpy(client, """
        SELECT project, sum(count) AS n FROM pypi.pypi_downloads_per_day
        WHERE date BETWEEN '2025-01-01' AND '2025-12-31'
        GROUP BY project ORDER BY n DESC LIMIT 15""")
    ficha = clickpy(client, """
        SELECT toString(toStartOfMonth(date)), sum(count) FROM pypi.pypi_downloads_per_day
        WHERE project = 'fastapi' AND date < toStartOfMonth(today())
        GROUP BY 1 ORDER BY 1""")
    return {"ranking": [[p, int(n)] for p, n in ranking],
            "ficha": [[m, int(n)] for m, n in ficha]}


def sizes(blob: bytes) -> tuple[int, int, int]:
    return len(blob), len(gzip.compress(blob, 9)), len(brotli.compress(blob, quality=11))


def kb(n: int) -> str:
    return f"{n / 1024:,.0f} KB"


def serve(root: Path) -> tuple[http.server.ThreadingHTTPServer, int]:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

    handler = functools.partial(Quiet, directory=str(root))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def chrome(args: list[str]) -> str:
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
           "--virtual-time-budget=8000", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "build/spikes/s4")
    out.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=120, follow_redirects=True) as client:
        data = fetch_data(client)
        print(f"Datos: ranking {len(data['ranking'])} filas, ficha {len(data['ficha'])} meses "
              f"({data['ficha'][0][0]} → {data['ficha'][-1][0]})")
        data_json = json.dumps(data, separators=(",", ":"))

        (out / "probe.js").write_text(PROBE_JS)
        (out / "page.css").write_text(PAGE_CSS)
        (out / "echarts-init.js").write_text(ECHARTS_INIT)
        (out / "plotly-init.js").write_text(PLOTLY_INIT)
        css = out / "plotly.css"
        if not css.exists():
            css.write_bytes(client.get(PLOTLY_CSS).raise_for_status().content)

        print("\n## Peso (librería sola; página = librería + init + datos + probe/css)")
        print("build\tcrudo\tgzip\tbrotli\tpágina_brotli")
        for name, (url, engine) in LIBS.items():
            lib = out / f"{name}.js"
            if not lib.exists():
                lib.write_bytes(client.get(url).raise_for_status().content)
            init = f"{engine}-init.js"
            extra = '<link rel="stylesheet" href="plotly.css">' if engine == "plotly" else ""
            html = PAGE.format(csp=CSP, name=name, lib=lib.name, init=init, data=data_json,
                               extra_css=extra)
            (out / f"{name}.html").write_text(html)
            raw, gz, br = sizes(lib.read_bytes())
            parts = [lib, out / init, out / "probe.js", out / "page.css", out / f"{name}.html"]
            if engine == "plotly":
                parts.append(css)
            page_br = sum(sizes(p.read_bytes())[2] for p in parts)
            print(f"{name}\t{kb(raw)}\t{kb(gz)}\t{kb(br)}\t{kb(page_br)}")

    if not CHROME:
        print("\n(No hay Chrome/Chromium: se omite la prueba en navegador.)")
        return

    srv, port = serve(out)
    try:
        print("\n## Navegador (Chrome headless, CSP estricta)")
        print(f"CSP: {CSP}")
        for name in LIBS:
            url = f"http://127.0.0.1:{port}/{name}.html"
            dom = chrome(["--dump-dom", url])
            attr = lambda k: (m.group(1) if (m := re.search(rf'data-{k}="([^"]*)"', dom)) else "")
            status = attr("status") or "NO RENDERIZÓ"
            error = attr("error").replace("&quot;", '"')
            viol = json.loads(attr("violations").replace("&quot;", '"') or "[]")
            print(f"\n{name}: {status}" + (f" · error: {error}" if error else ""))
            for v in sorted(set(viol)):
                print(f"  violación CSP: {v}")
            for width, tag in ((1280, "desktop"), (390, "movil")):
                chrome([f"--window-size={width},1000", f"--screenshot={out / f'{name}-{tag}.png'}",
                        url])
        print(f"\nCapturas en {out}/*.png")
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
