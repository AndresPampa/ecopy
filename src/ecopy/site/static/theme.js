// Tema elegido a mano. Se carga sin defer para aplicarlo antes de pintar; sin elección guardada
// manda el sistema operativo. El botón nombra el tema al que cambia.
(() => {
  'use strict';
  const KEY = 'ecopy-theme';
  const root = document.documentElement;
  const system = matchMedia('(prefers-color-scheme: dark)');

  const saved = () => {
    try {
      const value = localStorage.getItem(KEY);
      return value === 'dark' || value === 'light' ? value : null;
    } catch {
      return null;
    }
  };
  const save = (theme) => {
    try {
      localStorage.setItem(KEY, theme);
    } catch {
      // Sin almacenamiento, el cambio dura lo que dure la página.
    }
  };
  const current = () => root.dataset.theme || (system.matches ? 'dark' : 'light');

  const initial = saved();
  if (initial) root.dataset.theme = initial;

  document.addEventListener('DOMContentLoaded', () => {
    const button = document.querySelector('.theme-toggle');
    const label = () => {
      const next = current() === 'dark' ? 'Light' : 'Dark';
      const text = button.dataset[`label${next}`];
      button.textContent = button.dataset[`name${next}`];
      button.setAttribute('aria-label', text);
      button.title = text;
    };
    button.addEventListener('click', () => {
      const next = current() === 'dark' ? 'light' : 'dark';
      root.dataset.theme = next;
      save(next);
      label();
      document.dispatchEvent(new CustomEvent('ecopy:theme'));
    });
    system.addEventListener('change', label);
    label();
    button.hidden = false;
  });
})();
