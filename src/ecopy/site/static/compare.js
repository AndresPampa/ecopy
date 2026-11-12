// Comparador sin servidor: lee un JSON por librería y guarda la selección en la URL. Los textos
// externos solo entran por textContent y por el codificador de ECharts.
(() => {
  'use strict';
  const MAX = 4;
  const root = document.getElementById('compare');
  const texts = JSON.parse(root.dataset.texts);
  const input = document.getElementById('compare-input');
  const names = document.getElementById('compare-names');
  const chosen = document.getElementById('compare-chosen');
  const message = document.getElementById('compare-message');
  const table = document.getElementById('compare-table');
  const box = document.getElementById('compare-chart');
  const lang = document.documentElement.lang;
  const compact = new Intl.NumberFormat(lang, { notation: 'compact', maximumFractionDigits: 3 });
  const percent = new Intl.NumberFormat(lang, { maximumFractionDigits: 3 });
  const full = new Intl.NumberFormat(lang);
  const chart = echarts.init(box, null, { renderer: 'svg' });
  const token = (name) => getComputedStyle(box).getPropertyValue(name).trim();

  const state = { measure: 'share', scale: 'linear', series: new Map(), slots: new Map() };
  let index = new Map();

  const say = (text) => {
    message.textContent = text;
  };
  const freeSlot = () => [1, 2, 3, 4].find((slot) => ![...state.slots.values()].includes(slot));
  const axisFormat = (v) => (state.measure === 'share' ? `${percent.format(v)}%` : compact.format(v));
  const tipFormat = (v) => (state.measure === 'share' ? `${percent.format(v)}%` : full.format(v));
  const valueOf = (v) => (state.scale === 'log' && v === 0 ? null : v);

  const syncUrl = () => {
    const query = new URLSearchParams([...state.series.keys()].map((p) => ['p', p])).toString();
    history.replaceState(null, '', query ? `?${query}` : location.pathname);
  };

  const renderChosen = () => {
    chosen.replaceChildren(
      ...[...state.series.keys()].map((project) => {
        const item = document.createElement('li');
        const button = document.createElement('button');
        const swatch = document.createElement('span');
        button.type = 'button';
        button.className = 'chip';
        button.setAttribute('aria-label', texts.remove.replace('{project}', project));
        swatch.className = `swatch slot-${state.slots.get(project)}`;
        button.append(swatch, document.createTextNode(`${project} ×`));
        button.addEventListener('click', () => remove(project));
        item.append(button);
        return item;
      })
    );
  };

  const renderTable = () => {
    const entries = [...state.series.values()];
    const head = document.createElement('tr');
    [texts.month, ...entries.map((s) => s.project)].forEach((title) => {
      const th = document.createElement('th');
      th.scope = 'col';
      th.textContent = title;
      head.append(th);
    });
    const months = [...new Set(entries.flatMap((s) => s.months))].sort().reverse();
    const lookups = entries.map((s) => new Map(s.months.map((m, i) => [m, s[state.measure][i]])));
    const body = months.map((month) => {
      const row = document.createElement('tr');
      const label = document.createElement('th');
      label.scope = 'row';
      label.textContent = month.slice(0, 7);
      row.append(label);
      lookups.forEach((values) => {
        const cell = document.createElement('td');
        const value = values.get(month);
        cell.textContent = value === null || value === undefined ? texts.noData : tipFormat(value);
        row.append(cell);
      });
      return row;
    });
    const thead = document.createElement('thead');
    const tbody = document.createElement('tbody');
    thead.append(head);
    tbody.append(...body);
    table.replaceChildren(thead, tbody);
  };

  const draw = () => {
    // Sin series, ECharts dibujaría un eje suelto: el gráfico no ocupa lugar hasta tener datos.
    box.hidden = state.series.size === 0;
    if (box.hidden) {
      chart.clear();
      return;
    }
    chart.resize();
    const text = token('--ink-2');
    const grid = token('--grid');
    const series = [...state.series.values()].map((entry) => {
      const color = token(`--series-${state.slots.get(entry.project)}`);
      return {
        name: entry.project,
        type: 'line',
        showSymbol: false,
        connectNulls: false,
        lineStyle: { width: 2, color },
        itemStyle: { color },
        endLabel: {
          show: true,
          color: text,
          formatter: (p) => echarts.format.encodeHTML(p.seriesName),
        },
        data: entry.months.map((m, i) => [m, valueOf(entry[state.measure][i])]),
      };
    });
    chart.setOption(
      {
        animation: false,
        grid: { left: 8, right: 96, top: 32, bottom: 8, containLabel: true },
        legend: { top: 0, left: 0, textStyle: { color: text } },
        tooltip: {
          trigger: 'axis',
          confine: true,
          backgroundColor: token('--surface'),
          borderColor: grid,
          textStyle: { color: token('--ink') },
          valueFormatter: (v) => (v === null || v === undefined ? texts.noData : tipFormat(v)),
        },
        xAxis: {
          type: 'time',
          axisLabel: { color: text, hideOverlap: true },
          axisLine: { lineStyle: { color: token('--axis') } },
          axisTick: { show: false },
          splitLine: { show: false },
        },
        yAxis: {
          type: state.scale === 'log' ? 'log' : 'value',
          ...(state.scale === 'log' ? {} : { min: 0 }),
          axisLabel: { color: text, formatter: axisFormat },
          splitLine: { lineStyle: { color: grid } },
        },
        series,
      },
      true
    );
  };

  const refresh = () => {
    renderChosen();
    renderTable();
    draw();
    syncUrl();
    if (state.series.size === 0) say(texts.empty);
  };

  function remove(project) {
    state.series.delete(project);
    state.slots.delete(project);
    say('');
    refresh();
  }

  const add = async (project, { quiet = false } = {}) => {
    if (state.series.has(project)) return;
    if (!index.has(project)) {
      if (!quiet) say(texts.unknown);
      return;
    }
    if (state.series.size >= MAX) {
      say(texts.full);
      return;
    }
    const slot = freeSlot();
    state.slots.set(project, slot);
    try {
      const response = await fetch(`/data/library/${encodeURIComponent(index.get(project))}.json`);
      if (!response.ok) throw new Error(String(response.status));
      state.series.set(project, await response.json());
      say('');
    } catch {
      state.slots.delete(project);
      say(texts.failed);
    }
  };

  const toggle = (attribute, key) => {
    root.querySelectorAll(`[${attribute}]`).forEach((button) => {
      button.addEventListener('click', () => {
        state[key] = button.getAttribute(attribute);
        root
          .querySelectorAll(`[${attribute}]`)
          .forEach((b) => b.setAttribute('aria-pressed', String(b === button)));
        renderTable();
        draw();
      });
    });
  };

  const submit = async () => {
    await add(input.value.trim());
    input.value = '';
    refresh();
  };

  (async () => {
    root.hidden = false;
    chart.resize();
    try {
      const response = await fetch('/data/library/index.json');
      index = new Map((await response.json()).map((item) => [item.project, item.slug]));
    } catch {
      box.hidden = true;
      say(texts.failed);
      return;
    }
    names.replaceChildren(
      ...[...index.keys()].map((project) => {
        const option = document.createElement('option');
        option.value = project;
        return option;
      })
    );
    toggle('data-measure', 'measure');
    toggle('data-scale', 'scale');
    document.getElementById('compare-add').addEventListener('click', submit);
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') submit();
    });
    window.addEventListener('resize', () => chart.resize());
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', draw);
    document.addEventListener('ecopy:theme', draw);
    const requested = new URLSearchParams(location.search).getAll('p').slice(0, MAX);
    for (const project of requested) await add(project, { quiet: true });
    refresh();
  })();
})();
