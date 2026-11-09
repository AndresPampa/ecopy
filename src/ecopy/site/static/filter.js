// Filtro por tags del catálogo: varios tags se combinan con AND y quedan en la URL.
(() => {
  'use strict';
  const panel = document.getElementById('filters');
  const count = document.getElementById('filter-count');
  const rows = [...document.querySelectorAll('tr[data-tags]')];
  const buttons = [...panel.querySelectorAll('[data-tag]')];
  const known = new Set(buttons.map((b) => b.dataset.tag));
  const active = new Set(new URLSearchParams(location.search).getAll('tag').filter((t) => known.has(t)));

  const apply = () => {
    let shown = 0;
    rows.forEach((row) => {
      const tags = new Set(row.dataset.tags.split(' '));
      const visible = [...active].every((tag) => tags.has(tag));
      row.hidden = !visible;
      shown += visible ? 1 : 0;
    });
    buttons.forEach((b) => b.setAttribute('aria-pressed', String(active.has(b.dataset.tag))));
    count.textContent = count.dataset.template.replace('{shown}', shown).replace('{total}', rows.length);
    const query = new URLSearchParams([...active].map((tag) => ['tag', tag])).toString();
    history.replaceState(null, '', query ? `?${query}` : location.pathname);
  };

  buttons.forEach((button) =>
    button.addEventListener('click', () => {
      const tag = button.dataset.tag;
      if (active.has(tag)) active.delete(tag);
      else active.add(tag);
      apply();
    })
  );
  panel.hidden = false;
  apply();
})();
