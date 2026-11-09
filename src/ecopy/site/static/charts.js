// Dibuja los gráficos de barras de la página de un año a partir del JSON de la página. Sin
// contenido externo: los datos son números y etiquetas de la taxonomía de ecopy.
(() => {
  'use strict';
  const lang = document.documentElement.lang;
  const compact = new Intl.NumberFormat(lang, { notation: 'compact', maximumFractionDigits: 1 });
  const percent = new Intl.NumberFormat(lang, { maximumFractionDigits: 1 });
  const formats = {
    compact: (v) => compact.format(v),
    percent: (v) => `${percent.format(v)}%`,
  };

  document.querySelectorAll('[data-chart]').forEach((container) => {
    const { option, format } = JSON.parse(
      document.getElementById(`${container.id}-data`).textContent
    );
    const show = formats[format];
    const chart = echarts.init(container, null, { renderer: 'svg' });
    const token = (name) => getComputedStyle(container).getPropertyValue(name).trim();

    const draw = () => {
      const text = token('--text-secondary');
      const grid = token('--chart-grid');
      const themed = structuredClone(option);
      const line = { lineStyle: { color: grid } };
      [themed.xAxis, themed.yAxis].forEach((axis) => {
        Object.assign(axis, { axisLine: line, axisTick: { show: false } });
        axis.axisLabel = { ...axis.axisLabel, color: text };
        if (axis.type === 'value') {
          axis.axisLabel.formatter = (v) => show(v);
          axis.splitLine = line;
        }
      });
      Object.assign(themed.tooltip, {
        formatter: (p) => {
          const value = typeof p.value === 'object' ? p.value.value : p.value;
          return `${echarts.format.encodeHTML(p.name)}: ${show(value)}`;
        },
        backgroundColor: token('--surface'),
        borderColor: grid,
        textStyle: { color: token('--text-primary') },
      });
      themed.series.forEach((series) => {
        series.itemStyle = { ...series.itemStyle, color: token('--chart-line') };
      });
      chart.setOption(themed, true);
    };

    draw();
    window.addEventListener('resize', () => chart.resize());
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', draw);
  });
})();
