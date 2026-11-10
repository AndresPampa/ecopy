// Dibuja los gráficos de una página a partir de su JSON. Sin contenido externo: los datos son
// números y etiquetas de ecopy.
(() => {
  'use strict';
  const lang = document.documentElement.lang;
  const compact = new Intl.NumberFormat(lang, { notation: 'compact', maximumFractionDigits: 1 });
  const percent = new Intl.NumberFormat(lang, { maximumFractionDigits: 2 });
  const full = new Intl.NumberFormat(lang);
  const monthName = new Intl.DateTimeFormat(lang, {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });
  const formats = {
    compact: { axis: (v) => compact.format(v), tip: (v) => compact.format(v) },
    full: { axis: (v) => compact.format(v), tip: (v) => full.format(v) },
    percent: { axis: (v) => `${percent.format(v)}%`, tip: (v) => `${percent.format(v)}%` },
  };
  const value = (p) => (Array.isArray(p.value) ? p.value[1] : p.value?.value ?? p.value);

  document.querySelectorAll('[data-chart]').forEach((container) => {
    const payload = JSON.parse(document.getElementById(`${container.id}-data`).textContent);
    const { option, format, inProgress, labels } = payload;
    const show = formats[format];
    const chart = echarts.init(container, null, { renderer: 'svg' });
    const token = (name) => getComputedStyle(container).getPropertyValue(name).trim();

    const lineTooltip = (params) => {
      const month = params[0].value[0];
      const point = params.find((p) => value(p) !== null && value(p) !== undefined);
      if (inProgress && month === inProgress.month) {
        const partial = inProgress.downloads === null ? labels.noData : show.tip(inProgress.downloads);
        return `${monthName.format(new Date(month))}<br>${partial} · ${labels.inProgress}`;
      }
      return `${monthName.format(new Date(month))}<br>${point ? show.tip(value(point)) : labels.noData}`;
    };
    const barTooltip = (p) => `${echarts.format.encodeHTML(p.name)}: ${show.tip(value(p))}`;

    const draw = () => {
      const text = token('--ink-2');
      const grid = token('--grid');
      const axisLine = token('--axis');
      const series = token('--series');
      const themed = structuredClone(option);
      const rule = { lineStyle: { color: grid } };
      [themed.xAxis, themed.yAxis].forEach((axis) => {
        Object.assign(axis, { axisLine: { lineStyle: { color: axisLine } }, axisTick: { show: false } });
        axis.axisLabel = { ...axis.axisLabel, color: text };
        if (axis.type === 'value') {
          axis.axisLabel.formatter = (v) => show.axis(v);
          axis.splitLine = rule;
        }
      });
      Object.assign(themed.tooltip, {
        formatter: labels ? lineTooltip : barTooltip,
        backgroundColor: token('--surface'),
        borderColor: grid,
        textStyle: { color: token('--ink') },
      });
      if (themed.tooltip.axisPointer) themed.tooltip.axisPointer.lineStyle = { color: text };
      themed.series.forEach((s) => {
        s.itemStyle = { ...s.itemStyle, color: series };
        if (s.lineStyle) s.lineStyle.color = series;
        if (s.markArea) s.markArea.itemStyle = { color: token('--band') };
        if (s.markLine) {
          s.markLine.lineStyle = { color: axisLine, type: 'solid', width: 1 };
          s.markLine.label.color = text;
        }
      });
      chart.setOption(themed, true);
    };

    draw();
    window.addEventListener('resize', () => chart.resize());
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', draw);
    document.addEventListener('ecopy:theme', draw);
  });
})();
