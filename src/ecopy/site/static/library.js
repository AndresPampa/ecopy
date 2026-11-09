// Dibuja el gráfico de la ficha a partir del JSON de la página. Sin contenido externo: los
// datos son números y los textos salen de las plantillas de ecopy.
(() => {
  'use strict';
  const container = document.getElementById('chart');
  const { option, inProgressMonth, labels } = JSON.parse(
    document.getElementById('chart-data').textContent
  );
  const lang = document.documentElement.lang;
  const compact = new Intl.NumberFormat(lang, { notation: 'compact', maximumFractionDigits: 1 });
  const full = new Intl.NumberFormat(lang);
  const monthName = new Intl.DateTimeFormat(lang, {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });
  const chart = echarts.init(container, null, { renderer: 'svg' });
  const token = (name) => getComputedStyle(container).getPropertyValue(name).trim();

  const tooltip = (params) => {
    const month = params[0].value[0];
    const point = params.find((p) => p.value[1] !== null && p.value[1] !== undefined);
    const value = point ? full.format(point.value[1]) : labels.noData;
    const suffix = month === inProgressMonth ? ` · ${labels.inProgress}` : '';
    return `${monthName.format(new Date(month))}<br>${value}${suffix}`;
  };

  const draw = () => {
    const text = token('--text-secondary');
    const grid = token('--chart-grid');
    const line = token('--chart-line');
    const themed = structuredClone(option);
    const axis = { lineStyle: { color: grid } };
    Object.assign(themed.xAxis, { axisLine: axis, axisTick: axis });
    themed.xAxis.axisLabel.color = text;
    Object.assign(themed.yAxis, {
      splitLine: axis,
      axisLabel: { color: text, formatter: (v) => compact.format(v) },
    });
    Object.assign(themed.tooltip, {
      formatter: tooltip,
      backgroundColor: token('--surface'),
      borderColor: grid,
      textStyle: { color: token('--text-primary') },
    });
    themed.tooltip.axisPointer.lineStyle = { color: text };
    themed.series.forEach((series) => {
      series.lineStyle.color = line;
      series.itemStyle = { color: line };
    });
    chart.setOption(themed, true);
  };

  draw();
  window.addEventListener('resize', () => chart.resize());
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', draw);
})();
