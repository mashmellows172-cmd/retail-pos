/* RetailPOS Pro — shell iOS, estado y navegación. */
(() => {
  'use strict';

  const state = {
    carrier: 'TODAS',
    query: '',
    brand: '',
    minDcto: '',
    maxPrice: '',
    results: [],
    stats: {},
    selected: null,
    view: 'search',
    page: 1,
    pageSize: 40,
    loading: false,
    hasData: null,
    forceAll: false,
    isDesktop: false,
    lastFocus: null,
    range: null,
  };

  const $ = (id) => document.getElementById(id);
  const views = ['search', 'stats', 'config'];

  function setView(view) {
    if (!views.includes(view)) return;
    state.view = view;
    document.querySelectorAll('.view').forEach((section) => {
      const active = section.dataset.view === view;
      section.hidden = !active;
      section.classList.toggle('active', active);
    });
    document.querySelectorAll('.tabbar-item').forEach((button) => {
      const active = button.dataset.view === view;
      button.classList.toggle('active', active);
      if (active) button.setAttribute('aria-current', 'page');
      else button.removeAttribute('aria-current');
    });
    document.querySelectorAll('.desktop-nav-item').forEach((button) => {
      const active = button.dataset.view === view;
      button.classList.toggle('active', active);
      if (active) button.setAttribute('aria-current', 'page');
      else button.removeAttribute('aria-current');
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
    if (view === 'search') {
      const input = $('searchInput');
      if (input && state.isDesktop) input.focus();
    }
  }

  function formatRange(desde, hasta) {
    if (!desde || !hasta) return '';
    const meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sept', 'oct', 'nov', 'dic'];
    const a = new Date(`${desde}T12:00:00`);
    const b = new Date(`${hasta}T12:00:00`);
    if (Number.isNaN(a.getTime()) || Number.isNaN(b.getTime())) return '';
    const diaA = a.getDate();
    const diaB = b.getDate();
    const mesA = meses[a.getMonth()];
    const mesB = meses[b.getMonth()];
    return mesA === mesB ? `${diaA}–${diaB} ${mesA}` : `${diaA} ${mesA} – ${diaB} ${mesB}`;
  }

  function renderWeek(range) {
    const el = $('headerWeek');
    if (!el) return;
    state.range = range || null;
    if (!range || !range.semana || !range.desde || !range.hasta) {
      el.textContent = 'Sin precios cargados';
      return;
    }
    el.textContent = `Semana ${range.semana} · ${formatRange(range.desde, range.hasta)}`;
  }

  function updateOnlineStatus() {
    const online = navigator.onLine;
    const banner = $('offlineBanner');
    const text = $('connectionText');
    const dot = $('connectionDot');
    const diag = $('diagOffline');
    if (banner) banner.hidden = online;
    if (text) text.textContent = online ? 'En línea' : 'Sin conexión';
    if (dot) dot.classList.toggle('offline', !online);
    if (diag) diag.textContent = online ? 'En línea' : 'Sin conexión';
  }

  function showToast(message, type = 'info') {
    const container = $('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
    toast.textContent = message;
    container.appendChild(toast);
    window.setTimeout(() => toast.remove(), 2200);
  }

  function bindShell() {
    document.querySelectorAll('[data-view]').forEach((button) => {
      button.addEventListener('click', () => setView(button.dataset.view));
    });
    document.querySelectorAll('[data-goto]').forEach((button) => {
      button.addEventListener('click', () => setView(button.dataset.goto));
    });
    const clear = $('btnClearSearch');
    if (clear) {
      clear.addEventListener('click', () => {
        const input = $('searchInput');
        if (input) input.value = '';
        state.query = '';
        clear.hidden = true;
        input?.focus();
      });
    }
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
  }

  function init() {
    state.isDesktop = window.matchMedia('(min-width: 1024px)').matches;
    bindShell();
    updateOnlineStatus();
    renderWeek(null);
    setView('search');
  }

  window.RetailPOS = { state, setView, renderWeek, showToast };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
