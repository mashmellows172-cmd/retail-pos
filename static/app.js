/* RetailPOS Pro — shell iOS, búsqueda y navegación. */
(() => {
  'use strict';

  const PAGE_MOBILE = 40;
  const PAGE_DESKTOP = 50;

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
    excelName: null,
    csvName: null,
    version: null,
    installPrompt: null,
    lastSearch: null,
  };

  const $ = (id) => document.getElementById(id);
  const views = ['search', 'stats', 'config'];
  const carrierValues = ['TODAS', 'CLARO', 'WOM', 'ENTEL'];
  let searchTimer = null;
  let desktopQuery = null;

  const escapeHtml = (value) => String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  function formatCLP(value) {
    const number = Number(value || 0);
    return `$${number.toLocaleString('es-CL')}`;
  }

  function formatDiscount(value) {
    const number = Number(value || 0);
    return number > 0 ? `-${formatCLP(number)}` : '$0';
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
    if (view === 'search') {
      const input = $('searchInput');
      if (input && state.isDesktop) input.focus();
    }
    if (view === 'stats') renderStats();
    if (view === 'config') renderConfig();
    window.scrollTo({ top: 0, behavior: 'smooth' });
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
    const bannerText = $('offlineBannerText');
    if (bannerText) {
      bannerText.textContent = !online && state.results.length
        ? 'Sin conexión — mostrando datos guardados'
        : 'Sin conexión';
    }
  }

  function saveLastSearch() {
    try {
      localStorage.setItem('retailpos:lastSearch:v1', JSON.stringify({
        query: state.query,
        carrier: state.carrier,
        results: state.results,
        savedAt: Date.now(),
      }));
    } catch {
      /* almacenamiento lleno o bloqueado */
    }
  }

  function loadLastSearch() {
    try {
      const raw = localStorage.getItem('retailpos:lastSearch:v1');
      if (!raw) return null;
      const saved = JSON.parse(raw);
      if (!saved || !Array.isArray(saved.results)) return null;
      return saved;
    } catch {
      return null;
    }
  }

  function restoreLastSearch() {
    const saved = loadLastSearch();
    if (!saved || !saved.results.length) return false;
    state.query = saved.query || '';
    if (carrierValues.includes(saved.carrier)) state.carrier = saved.carrier;
    state.results = saved.results;
    state.selected = null;
    state.page = 1;
    state.lastSearch = saved;
    const input = $('searchInput');
    if (input) input.value = state.query;
    updateCarrierUI();
    renderResults();
    updateOnlineStatus();
    return true;
  }

  function restoreLastSearchForCurrentQuery() {
    const saved = loadLastSearch();
    if (!saved) return false;
    const sameQuery = String(saved.query || '').trim() === state.query.trim();
    const sameCarrier = String(saved.carrier || 'TODAS') === state.carrier;
    if (!sameQuery || !sameCarrier) return false;
    return restoreLastSearch();
  }

  function setBackgroundInert(value) {
    document.querySelectorAll('header, .tabbar').forEach((el) => {
      el.inert = value;
    });
  }

  function trapFocus(container, event) {
    if (event.key !== 'Tab') return;
    const focusables = Array.from(container.querySelectorAll('button, input, select, a[href], [tabindex]:not([tabindex="-1"])'))
      .filter((el) => !el.disabled && el.getBoundingClientRect().width > 0);
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
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

  function showState(name) {
    ['initialState', 'skeletonState', 'noDataState', 'emptyState', 'errorState', 'offlineState'].forEach((id) => {
      const el = $(id);
      if (el) el.hidden = id !== name;
    });
    const panel = $('resultsPanel');
    if (panel) panel.hidden = true;
    const loadMore = $('loadMore');
    if (loadMore) loadMore.hidden = true;
  }

  function updateCounts() {
    const stats = state.stats || {};
    const totals = {};
    carrierValues.forEach((op) => {
      if (op === 'TODAS') return;
      totals[op] = Number(stats[op]?.total || 0);
      const el = $(`count${op}`);
      if (el) el.textContent = totals[op].toLocaleString('es-CL');
    });
    const total = Object.values(totals).reduce((sum, value) => sum + value, 0);
    const all = $('countTODAS');
    if (all) all.textContent = total.toLocaleString('es-CL');
  }

  function updateCarrierUI() {
    document.querySelectorAll('.segment').forEach((button) => {
      const active = button.dataset.carrier === state.carrier;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', active ? 'true' : 'false');
    });
  }

  function setCarrier(op, options = {}) {
    if (!carrierValues.includes(op)) return;
    const changed = state.carrier !== op;
    state.carrier = op;
    state.page = 1;
    if (changed) {
      state.brand = '';
      const select = $('brandFilter');
      if (select) select.value = '';
      updateFilterIndicators();
    }
    updateCarrierUI();
    loadBrands();
    if (options.search !== false) performSearch();
  }

  function applyUrlCarrier() {
    const op = (new URLSearchParams(location.search).get('op') || '').toUpperCase();
    if (carrierValues.includes(op) && op !== 'TODAS') {
      state.carrier = op;
      updateCarrierUI();
      return true;
    }
    return false;
  }

  function updateFilterIndicators() {
    const active = [state.brand, state.minDcto, state.maxPrice].filter((value) => String(value || '').trim() !== '');
    const count = active.length;
    const bar = $('activeFiltersBar');
    const text = $('activeFiltersText');
    const badge = $('activeFilterCount');
    if (bar) bar.hidden = count === 0;
    if (text) text.textContent = `${count} ${count === 1 ? 'filtro activo' : 'filtros activos'}`;
    if (badge) {
      badge.hidden = count === 0;
      badge.textContent = String(count);
    }
  }

  function readFilters() {
    state.brand = $('brandFilter')?.value || '';
    state.minDcto = $('minDctoFilter')?.value || '';
    state.maxPrice = $('maxPriceFilter')?.value || '';
    updateFilterIndicators();
  }

  function clearFilters() {
    if ($('brandFilter')) $('brandFilter').value = '';
    if ($('minDctoFilter')) $('minDctoFilter').value = '';
    if ($('maxPriceFilter')) $('maxPriceFilter').value = '';
    state.brand = '';
    state.minDcto = '';
    state.maxPrice = '';
    state.forceAll = false;
    state.page = 1;
    updateFilterIndicators();
  }

  function openFilters() {
    const sheet = $('filterSheet');
    const backdrop = $('filterBackdrop');
    if (!sheet) return;
    state.lastFocus = document.activeElement;
    sheet.hidden = false;
    if (backdrop) backdrop.hidden = false;
    sheet.setAttribute('aria-modal', 'true');
    $('filterClose')?.focus();
  }

  function closeFilters(restore = true) {
    const sheet = $('filterSheet');
    const backdrop = $('filterBackdrop');
    if (!sheet) return;
    sheet.hidden = true;
    if (backdrop) backdrop.hidden = true;
    if (state.isDesktop) sheet.hidden = false;
    if (restore && state.lastFocus && typeof state.lastFocus.focus === 'function') state.lastFocus.focus();
  }

  async function loadBrands() {
    const select = $('brandFilter');
    if (!select) return;
    const previous = state.brand;
    try {
      const params = new URLSearchParams();
      if (state.carrier !== 'TODAS') params.set('operadora', state.carrier);
      const res = await fetch(`/api/brands${params.toString() ? `?${params}` : ''}`);
      if (!res.ok) return;
      const brands = await res.json();
      select.innerHTML = '<option value="">Todas las marcas</option>' +
        (Array.isArray(brands) ? brands.map((brand) => `<option value="${escapeHtml(brand)}">${escapeHtml(brand)}</option>`).join('') : '');
      if (previous && Array.from(select.options).some((option) => option.value === previous)) select.value = previous;
    } catch {
      /* las marcas no bloquean la búsqueda */
    }
  }

  async function fetchPing() {
    try {
      const res = await fetch('/api/ping');
      if (!res.ok) throw new Error('ping');
      const data = await res.json();
      if (data.offline) throw new Error('offline');
      state.hasData = Boolean(data.excel);
      state.excelName = data.excel_name || null;
      state.csvName = data.csv_name || null;
      state.version = data.version || null;
      if (!state.hasData) {
        if (!state.results.length) showState('noData');
        renderWeek(null);
      }
      renderConfig();
    } catch {
      state.hasData = null;
    }
  }

  async function fetchStats() {
    try {
      const res = await fetch('/api/stats');
      if (!res.ok) throw new Error('stats');
      const data = await res.json();
      const stats = data || {};
      state.stats = stats;
      renderWeek(stats._rango || null);
      updateCounts();
      if (state.view === 'stats') renderStats();
    } catch {
      if (state.range === null) renderWeek(null);
      const grid = $('statsGrid');
      if (grid && state.view === 'stats') {
        grid.innerHTML = '<div class="stat-card group"><div class="stat-name">No pudimos cargar las estadísticas</div><p class="row-sub">Revisa la conexión e inténtalo otra vez.</p><button id="btnStatsRetry" class="button secondary block" type="button">Reintentar</button></div>';
        $('btnStatsRetry')?.addEventListener('click', fetchStats);
      }
    }
  }

  async function fetchCsvStatus() {
    try {
      const res = await fetch('/api/csv-status');
      const data = await res.json();
      if (data.ok && data.records > 0) {
        const count = Number(data.records).toLocaleString('es-CL');
        if ($('configCsvName') && !state.csvName) $('configCsvName').textContent = `${count} códigos cargados`;
      }
    } catch {
      /* estado secundario */
    }
  }

  function buildSearchParams() {
    const params = new URLSearchParams();
    if (state.query.trim()) params.set('q', state.query.trim());
    if (state.carrier !== 'TODAS') params.set('op', state.carrier);
    if (state.brand) params.set('marca', state.brand);
    if (state.minDcto) params.set('min_dcto', state.minDcto);
    if (state.maxPrice) params.set('max_precio', state.maxPrice);
    return params;
  }

  let searchSeq = 0;

  async function performSearch(resetPage = true) {
    if (state.view !== 'search') return;
    if (!state.query.trim() && !state.brand && !state.minDcto && !state.maxPrice && !state.forceAll) {
      state.results = [];
      state.page = 1;
      updateCountsLabel(0, 0, true);
      showState('initialState');
      return;
    }
    const seq = ++searchSeq;
    if (!navigator.onLine) {
      if (!restoreLastSearchForCurrentQuery()) {
        state.results = [];
        state.selected = null;
        state.page = 1;
        updateCountsLabel(0, 0, true);
        showState('offlineState');
      }
      return;
    }

    state.loading = true;
    showState('skeletonState');
    const params = buildSearchParams();
    try {
      const res = await fetch(`/api/search${params.toString() ? `?${params}` : ''}`);
      if (seq !== searchSeq) return;
      const payload = await res.json().catch(() => null);
      if (res.status === 503 || payload?.offline) {
        const error = new Error('Sin conexión');
        error.offline = true;
        throw error;
      }
      if (!res.ok || !Array.isArray(payload)) throw new Error('search');
      state.results = payload;
      if (resetPage) state.page = 1;
      state.selected = null;
      state.hasData = true;
      state.lastSearch = { query: state.query, carrier: state.carrier, results: payload, savedAt: Date.now() };
      saveLastSearch();
      renderResults();
      const input = $('searchInput');
      if (input) input.focus({ preventScroll: true });
    } catch (error) {
      if (seq !== searchSeq) return;
      if (error.offline) {
        if (!restoreLastSearchForCurrentQuery()) {
          state.results = [];
          state.selected = null;
          state.page = 1;
          updateCountsLabel(0, 0, true);
          showState('offlineState');
        }
      } else {
        showState('errorState');
        state.results = [];
      }
    } finally {
      if (seq === searchSeq) state.loading = false;
    }
  }

  function updateCountsLabel(shown, total, initial = false) {
    const el = $('resultsCount');
    if (!el) return;
    if (initial) {
      el.textContent = '';
      return;
    }
    el.textContent = shown < total ? `${shown} de ${total} productos` : `${total} ${total === 1 ? 'producto' : 'productos'}`;
  }

  function renderResults() {
    if (state.view !== 'search') return;
    const panel = $('resultsPanel');
    if (!state.results.length) {
      updateCountsLabel(0, 0);
      showState('emptyState');
      return;
    }
    ['initialState', 'skeletonState', 'noDataState', 'emptyState', 'errorState', 'offlineState'].forEach((id) => {
      const el = $(id);
      if (el) el.hidden = true;
    });
    if (panel) panel.hidden = false;
    state.pageSize = state.isDesktop ? 50 : 40;
    if (state.isDesktop) {
      if (state.selected == null && state.results.length) {
        state.selected = 0;
        renderDetail($('desktopDetail'), state.results[0]);
      }
      renderDesktopTable();
    } else {
      renderMobileList();
    }
    updateLoadMore();
  }

  function visibleResults() {
    return state.results.slice(0, state.page * state.pageSize);
  }

  function renderMobileList() {
    const list = $('resultsList');
    if (!list) return;
    const rows = visibleResults();
    list.innerHTML = rows.map((product, index) => {
      const carrier = escapeHtml(product.operadora || '');
      const brand = escapeHtml(product.marca || 'GENÉRICO');
      const description = escapeHtml(product.descripcion || 'Sin descripción');
      const plu = escapeHtml(product.plu_cod || '');
      return `<button class="result-row" type="button" data-index="${index}">
        <span class="result-main">
          <span class="result-meta"><span class="carrier-pill carrier-${carrier}">${carrier}</span><span class="brand-text">${brand}</span></span>
          <span class="result-name">${description}</span>
          <span class="result-sub">PLU ${plu}</span>
        </span>
        <span class="result-price">
          <span><span class="result-discount">${formatDiscount(product.descuento)}</span><span class="result-final">${formatCLP(product.precio_final)}</span></span>
          <svg class="icon chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </span>
      </button>`;
    }).join('');
    updateCountsLabel(rows.length, state.results.length);
  }

  function renderDesktopTable() {
    const body = $('desktopTableBody');
    if (!body) return;
    const rows = visibleResults();
    body.innerHTML = rows.map((product, index) => {
      const carrier = escapeHtml(product.operadora || '');
      const brand = escapeHtml(product.marca || 'GENÉRICO');
      const description = escapeHtml(product.descripcion || 'Sin descripción');
      const selected = state.selected === index ? ' class="selected"' : '';
      return `<tr data-index="${index}"${selected}>
        <td><span class="carrier-pill carrier-${carrier}">${carrier}</span></td>
        <td><div class="table-name">${description}</div><div class="table-sub">${brand}</div></td>
        <td class="mono">${escapeHtml(product.plu_cod || '')}</td>
        <td class="result-discount">${formatDiscount(product.descuento)}</td>
        <td class="result-final">${formatCLP(product.precio_final)}</td>
        <td><button class="table-action" type="button" data-action="detail" data-index="${index}">Ver códigos</button></td>
      </tr>`;
    }).join('');
    updateCountsLabel(rows.length, state.results.length);
  }

  function updateLoadMore() {
    const button = $('loadMore');
    if (!button) return;
    const hasMore = state.page * state.pageSize < state.results.length;
    button.hidden = !hasMore;
    button.textContent = state.isDesktop ? 'Cargar 50 más' : 'Cargar 40 más';
  }

  function clearSearch() {
    const input = $('searchInput');
    if (input) input.value = '';
    state.query = '';
    state.forceAll = false;
    state.page = 1;
    const clear = $('btnClearSearch');
    if (clear) clear.hidden = true;
    state.results = [];
    updateCountsLabel(0, 0, true);
    showState(state.hasData === false ? 'noDataState' : 'initialState');
  }

  function applyFiltersAndSearch() {
    readFilters();
    state.page = 1;
    closeFilters();
    performSearch();
  }

  function bindSearch() {
    const input = $('searchInput');
    if (!input) return;
    input.addEventListener('input', () => {
      state.query = input.value;
      state.forceAll = false;
      const clear = $('btnClearSearch');
      if (clear) clear.hidden = !input.value;
      if (searchTimer) window.clearTimeout(searchTimer);
      searchTimer = window.setTimeout(() => {
        performSearch();
      }, 300);
    });
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        if (searchTimer) window.clearTimeout(searchTimer);
        performSearch();
      }
    });
    $('btnClearSearch')?.addEventListener('click', () => {
      clearSearch();
      input.focus();
    });
    $('btnForceAll')?.addEventListener('click', () => {
      const field = $('searchInput');
      if (field) field.value = '';
      state.query = '';
      const clearBtn = $('btnClearSearch');
      if (clearBtn) clearBtn.hidden = true;
      state.forceAll = true;
      state.page = 1;
      performSearch();
    });
    $('btnEmptyClear')?.addEventListener('click', () => {
      clearFilters();
      clearSearch();
      input.focus();
    });
    $('btnRetry')?.addEventListener('click', () => performSearch());
    $('btnOfflineRetry')?.addEventListener('click', () => performSearch());
    $('btnClearFiltersInline')?.addEventListener('click', () => {
      clearFilters();
      performSearch();
    });
    $('loadMore')?.addEventListener('click', () => {
      state.page += 1;
      renderResults();
      updateLoadMore();
    });
  }

  function bindCarriers() {
    document.querySelectorAll('.segment').forEach((button) => {
      button.addEventListener('click', () => setCarrier(button.dataset.carrier));
    });
  }

  function bindFilters() {
    $('btnOpenFilters')?.addEventListener('click', openFilters);
    $('filterClose')?.addEventListener('click', () => closeFilters());
    $('filterBackdrop')?.addEventListener('click', () => closeFilters());
    $('applyFilters')?.addEventListener('click', applyFiltersAndSearch);
    $('filterClear')?.addEventListener('click', () => {
      clearFilters();
      performSearch();
    });
    ['brandFilter', 'minDctoFilter', 'maxPriceFilter'].forEach((id) => {
      $(id)?.addEventListener('change', () => {
        readFilters();
      });
    });
  }

  function bindResults() {
    $('resultsList')?.addEventListener('click', (event) => {
      const row = event.target.closest('.result-row');
      if (row) openDetail(Number(row.dataset.index), row);
    });
    $('desktopTableBody')?.addEventListener('click', (event) => {
      const button = event.target.closest('[data-action="detail"]');
      if (button) {
        openDetail(Number(button.dataset.index), button);
        return;
      }
      const row = event.target.closest('tr[data-index]');
      if (row) openDetail(Number(row.dataset.index), row);
    });
  }

  function bindShell() {
    document.querySelectorAll('button[data-view]').forEach((button) => {
      button.addEventListener('click', () => setView(button.dataset.view));
    });
    document.querySelectorAll('[data-goto]').forEach((button) => {
      button.addEventListener('click', () => setView(button.dataset.goto));
    });
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    window.addEventListener('beforeinstallprompt', (event) => {
      event.preventDefault();
      state.installPrompt = event;
      const container = $('pwaInstallContainer');
      if (container) container.hidden = false;
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeFilters();
        closeDetail();
      }
    });
    $('filterSheet')?.addEventListener('keydown', (event) => trapFocus($('filterSheet'), event));

    desktopQuery = window.matchMedia('(min-width: 1024px)');
    const applyLayout = (matches) => {
      state.isDesktop = matches;
      state.pageSize = matches ? PAGE_DESKTOP : PAGE_MOBILE;
      const sheet = $('filterSheet');
      if (sheet) {
        if (matches) {
          sheet.hidden = false;
          sheet.setAttribute('aria-modal', 'false');
          if ($('filterBackdrop')) $('filterBackdrop').hidden = true;
        } else {
          sheet.hidden = true;
          sheet.setAttribute('aria-modal', 'true');
        }
      }
      if (state.results.length) renderResults();
    };
    applyLayout(desktopQuery.matches);
    desktopQuery.addEventListener('change', (event) => applyLayout(event.matches));
  }

  function openDetail(index, opener) {
    const product = state.results[index];
    if (!product) return;
    state.selected = index;
    state.lastFocus = opener || document.activeElement;
    if (state.isDesktop) {
      renderDesktopTable();
      renderDetail($('desktopDetail'), product);
      return;
    }
    const dialog = $('detailDialog');
    if (!dialog) return;
    dialog.hidden = false;
    document.body.style.overflow = 'hidden';
    const main = document.querySelector('main');
    if (main) main.inert = true;
    setBackgroundInert(true);
    renderDetail($('detailBody'), product);
    $('detailBack')?.focus();
  }

  function closeDetail() {
    const dialog = $('detailDialog');
    if (!dialog || dialog.hidden) return;
    dialog.hidden = true;
    document.body.style.overflow = '';
    const main = document.querySelector('main');
    if (main) main.inert = false;
    setBackgroundInert(false);
    if (state.lastFocus && typeof state.lastFocus.focus === 'function') state.lastFocus.focus();
  }

  function barcodeUrl(code) {
    return `/api/barcode-inline/${encodeURIComponent(code)}?text=0&quiet_zone=4`;
  }

  function renderDetail(container, prod) {
    if (!container || !prod) return;
    const isDialog = container.id === 'detailBody';
    const title = $('detailTitle');
    const carrierLabel = $('detailCarrier');
    if (title && isDialog) title.textContent = prod.descripcion || 'Detalle';
    if (carrierLabel && isDialog) carrierLabel.textContent = `${prod.operadora || ''} · ${prod.marca || ''}`;
    const equipCode = String(prod.ean13 || prod.plu_cod || '');
    const planCode = prod.plan_barcode || '';
    const isEan = prod.ean13_source !== 'plu_raw' && prod.ean13_source !== 'invalid';
    const equipKind = isEan ? 'EAN-13' : 'PLU';
    const equipOrigin = prod.ean13_source === 'csv'
      ? 'CSV'
      : (isEan ? 'Calculado' : 'PLU sin EAN-13');
    const planImg = planCode
      ? `<img src="${barcodeUrl(planCode)}" alt="Código de barras del plan ${escapeHtml(prod.operadora || '')}" loading="lazy" decoding="async">`
      : '';
    const equipImg = equipCode
      ? `<img src="${barcodeUrl(equipCode)}" alt="Código de barras del equipo" loading="lazy" decoding="async">`
      : '';
    container.innerHTML = `
      <div class="detail-summary group">
        <div class="detail-name">${escapeHtml(prod.descripcion || 'Sin descripción')}</div>
        <div class="detail-meta"><span>PLU ${escapeHtml(prod.plu_cod || '')}</span><span class="dot-sep"></span><span>Vigencia ${escapeHtml(formatRange(prod.desde, prod.hasta))}</span></div>
        <div class="price-line">
          <div><div class="discount-big">${formatDiscount(prod.descuento)}</div><div class="old-price">Normal ${formatCLP(prod.precio)}</div></div>
          <div class="price-right"><div class="final-big">${formatCLP(prod.precio_final)}</div><div class="old-price">Precio final</div></div>
        </div>
        <div class="discount-copy"><button class="text-button js-copy" type="button" data-copy="${escapeHtml(String(prod.descuento || ''))}" data-label="Descuento">Copiar descuento</button></div>
      </div>
      <div class="section-title">Códigos para escanear</div>
      <section class="code-card group">
        <div class="code-head"><div class="code-label"><span class="step-chip">1</span>Código del equipo</div><span class="code-kind">${equipKind}</span></div>
        <div class="barcode-box">${equipImg}</div>
        <div class="code-foot"><button class="code-number" type="button" data-copy="${escapeHtml(equipCode)}" data-label="Código del equipo">${escapeHtml(equipCode || 'Sin código')}</button><button class="text-button code-copy" type="button" data-copy="${escapeHtml(equipCode)}" data-label="Código del equipo">Copiar</button></div>
      </section>
      <section class="code-card group">
        <div class="code-head"><div class="code-label"><span class="step-chip">2</span>Código del plan <span class="code-carrier">· ${escapeHtml(prod.operadora || '')}</span></div><span class="code-kind">COD BARRA</span></div>
        <div class="barcode-box ${planCode ? '' : 'empty'}">${planCode ? planImg : 'Sin código de plan'}</div>
        <div class="code-foot"><button class="code-number" type="button" data-copy="${escapeHtml(planCode)}" data-label="Código del plan">${escapeHtml(planCode || 'Sin código de plan')}</button><button class="text-button code-copy" type="button" data-copy="${escapeHtml(planCode)}" data-label="Código del plan" ${planCode ? '' : 'disabled'}>Copiar</button></div>
      </section>
      <details class="details-row group">
        <summary><span>Más detalles</span><svg class="icon chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></summary>
        <div class="details-body">
          <div class="detail-line"><span>PLU</span><b>${escapeHtml(prod.plu_cod || '')}</b></div>
          <div class="detail-line"><span>Origen EAN</span><b>${equipOrigin}</b></div>
          <div class="detail-line"><span>Vigencia</span><b>${escapeHtml(formatRange(prod.desde, prod.hasta))}</b></div>
          <div class="detail-line"><span>Precio normal</span><b>${formatCLP(prod.precio)}</b></div>
        </div>
      </details>
      ${isDialog ? '' : '<button class="button primary block js-print" type="button">Imprimir códigos</button>'}`;
    bindCopyButtons(container);
    container.querySelectorAll('.js-print').forEach((button) => {
      button.addEventListener('click', printCurrent);
    });
  }

  function setImageSource(img, src) {
    return new Promise((resolve) => {
      if (!img) {
        resolve(false);
        return;
      }
      img.onload = null;
      img.onerror = null;
      img.removeAttribute('src');
      if (!src) {
        resolve(false);
        return;
      }
      let settled = false;
      const done = (ok) => {
        if (settled) return;
        settled = true;
        img.onload = null;
        img.onerror = null;
        if (!ok) img.removeAttribute('src');
        resolve(ok);
      };
      img.onload = () => done(true);
      img.onerror = () => done(false);
      img.src = src;
      window.setTimeout(() => done(img.complete && img.naturalWidth > 0), 1500);
    });
  }

  async function printCurrent() {
    const prod = state.results[state.selected];
    if (!prod) {
      showToast('Selecciona un producto para imprimir', 'error');
      return;
    }
    const equipCode = String(prod.ean13 || prod.plu_cod || '');
    const planCode = prod.plan_barcode || '';
    const pluCode = String(prod.plu_cod || '');
    const setText = (id, value) => {
      const el = $(id);
      if (el) el.textContent = value;
    };
    setText('printCarrierBrand', `${prod.operadora || ''} • ${prod.marca || ''}`);
    setText('printDescription', prod.descripcion || 'Sin descripción');
    setText('printPlu', pluCode);
    setText('printVigencia', `Vigencia: ${formatRange(prod.desde, prod.hasta) || 'sin fecha'}`);
    setText('printDiscount', formatDiscount(prod.descuento));
    setText('printNormalPrice', formatCLP(prod.precio));
    setText('printFinalPrice', formatCLP(prod.precio_final));
    setText('printCarrierPlan', prod.operadora || '');
    setText('printEanNumber', equipCode);
    setText('printPluNumber', pluCode);
    document.getElementById('printPlanNumber').textContent = planCode;
    setText('printTimestamp', new Date().toLocaleString('es-CL'));
    const setBlock = (id, visible) => {
      const block = $(id);
      if (block) block.hidden = !visible;
    };
    setBlock('printEanBlock', Boolean(equipCode));
    setBlock('printPlanBlock', Boolean(planCode));
    setBlock('printPluBlock', Boolean(pluCode));
    const [eanOk, planOk, pluOk] = await Promise.all([
      setImageSource($('printEanImg'), equipCode ? barcodeUrl(equipCode) : ''),
      setImageSource($('printPlanImg'), planCode ? barcodeUrl(planCode) : ''),
      setImageSource($('printPluBarcodeImg'), pluCode ? barcodeUrl(pluCode) : ''),
    ]);
    if ((equipCode && !eanOk) || (planCode && !planOk) || (pluCode && !pluOk)) {
      showToast('Algún código de barras no se pudo generar', 'error');
    }
    window.print();
  }

  function bindCopyButtons(container) {
    container.querySelectorAll('[data-copy]').forEach((button) => {
      button.addEventListener('click', () => copyCode(button.dataset.copy, button.dataset.label || 'Código', button));
    });
  }

  function legacyCopy(text) {
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.cssText = 'position:fixed;top:-9999px;left:-9999px;opacity:0';
    document.body.appendChild(area);
    area.select();
    area.setSelectionRange(0, text.length);
    let ok = false;
    try {
      ok = document.execCommand('copy');
    } catch {
      ok = false;
    }
    area.remove();
    return ok;
  }

  async function copyCode(text, label, button) {
    if (!text) return;
    let copied = false;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        copied = true;
      } else {
        copied = legacyCopy(text);
      }
    } catch {
      copied = legacyCopy(text);
    }
    if (!copied) {
      showToast('No se pudo copiar', 'error');
      return;
    }
    showToast(`${label} copiado`, 'success');
    if (button && !button.dataset.originalText) {
      button.dataset.originalText = button.textContent;
      button.textContent = 'Copiado';
      window.setTimeout(() => {
        button.textContent = button.dataset.originalText;
        delete button.dataset.originalText;
      }, 1500);
    }
  }

  function renderStats() {
    const grid = $('statsGrid');
    if (!grid) return;
    const stats = state.stats || {};
    const range = stats._rango || state.range || null;
    const ops = Object.entries(stats).filter(([key]) => !key.startsWith('_'));
    if (!ops.length) {
      grid.innerHTML = `
        <div class="stat-card group">
          <div class="stat-name">Sin datos cargados</div>
          <p class="row-sub">Sube el Excel semanal para ver el resumen por operadora.</p>
          <button class="button secondary block" type="button" data-goto="config">Ir a Configuración</button>
        </div>`;
      grid.querySelectorAll('[data-goto]').forEach((button) => {
        button.addEventListener('click', () => setView(button.dataset.goto));
      });
      return;
    }
    grid.innerHTML = ops.map(([op, data]) => {
      const total = Number(data?.total || 0).toLocaleString('es-CL');
      const marcas = Number(data?.marcas || 0);
      const maxDcto = formatDiscount(data?.dcto_max);
      const min = formatCLP(data?.precio_min);
      const max = formatCLP(data?.precio_max);
      const week = range && range.semana ? `Semana ${range.semana}` : 'Sin semana';
      const vigencia = range && range.desde && range.hasta ? formatRange(range.desde, range.hasta) : '';
      return `<article class="stat-card group">
        <div class="stat-top">
          <span class="stat-drop carrier-${escapeHtml(op)}" aria-hidden="true"></span>
          <span class="stat-name">${escapeHtml(op)}</span>
          <span class="stat-brands">${marcas} ${marcas === 1 ? 'marca' : 'marcas'}</span>
        </div>
        <div class="stat-total">${total}</div>
        <div class="stat-label">productos vigentes</div>
        <div class="stat-row"><span>Máx. descuento</span><span class="result-discount">${maxDcto}</span></div>
        <div class="stat-row"><span>Rango de precios</span><span class="mono">${min} – ${max}</span></div>
        <div class="stat-row"><span>Vigencia</span><span>${escapeHtml(week)}${vigencia ? ` · ${escapeHtml(vigencia)}` : ''}</span></div>
        <div class="stat-link"><button class="text-button" type="button" data-stats-op="${escapeHtml(op)}">Ver productos</button></div>
      </article>`;
    }).join('');
    grid.querySelectorAll('[data-stats-op]').forEach((button) => {
      button.addEventListener('click', () => {
        state.forceAll = true;
        setView('search');
        setCarrier(button.dataset.statsOp);
      });
    });
  }

  function setUploadState(kind, busy, message) {
    const spinner = $(kind === 'excel' ? 'excelLoadingSpinner' : 'csvLoadingSpinner');
    const button = $(kind === 'excel' ? 'btnSelectExcel' : 'btnSelectCsv');
    if (spinner) {
      spinner.hidden = !busy;
      if (busy) spinner.lastChild.textContent = message || 'Procesando…';
    }
    if (button) button.disabled = busy;
  }

  async function uploadExcel(file) {
    if (!file) return;
    setUploadState('excel', true, 'Procesando Excel…');
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch('/api/upload-excel', { method: 'POST', body: form });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) throw new Error(data.error || 'No se pudo procesar el Excel');
      state.excelName = data.excel_name || file.name;
      state.hasData = true;
      showToast('Excel actualizado', 'success');
      await fetchPing();
      await fetchStats();
      await loadBrands();
      state.results = [];
      state.selected = null;
      state.page = 1;
      state.forceAll = true;
      setView('search');
      await performSearch();
    } catch (error) {
      showToast(error.message || 'No se pudo procesar el Excel', 'error');
    } finally {
      setUploadState('excel', false);
      const input = $('excelFileInput');
      if (input) input.value = '';
    }
  }

  async function uploadCsv(file) {
    if (!file) return;
    setUploadState('csv', true, 'Procesando CSV…');
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch('/api/upload-csv', { method: 'POST', body: form });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) throw new Error(data.error || 'No se pudo procesar el CSV');
      state.csvName = data.csv_name || file.name;
      showToast(`${Number(data.records || 0).toLocaleString('es-CL')} códigos cargados`, 'success');
      await fetchPing();
      await fetchCsvStatus();
      state.results = [];
      state.selected = null;
      state.page = 1;
      state.forceAll = true;
      setView('search');
      await performSearch();
    } catch (error) {
      showToast(error.message || 'No se pudo procesar el CSV', 'error');
    } finally {
      setUploadState('csv', false);
      const input = $('csvFileInput');
      if (input) input.value = '';
    }
  }

  function renderConfig() {
    const excel = $('configExcelName');
    const csv = $('configCsvName');
    if (excel) excel.textContent = state.excelName || 'Sin archivo';
    if (csv) csv.textContent = state.csvName || 'Sin archivo';
    const version = $('diagVersion');
    if (version && state.version) version.textContent = `v${state.version}`;
    const sw = $('diagSwStatus');
    if (sw) {
      if (!('serviceWorker' in navigator)) sw.textContent = 'No soportado';
      else if (navigator.serviceWorker.controller) sw.textContent = 'Activo';
      else sw.textContent = 'Sin registrar';
    }
  }

  function bindConfig() {
    $('btnSelectExcel')?.addEventListener('click', () => $('excelFileInput')?.click());
    $('btnSelectCsv')?.addEventListener('click', () => $('csvFileInput')?.click());
    $('excelFileInput')?.addEventListener('change', (event) => uploadExcel(event.target.files?.[0]));
    $('csvFileInput')?.addEventListener('change', (event) => uploadCsv(event.target.files?.[0]));
    $('btnReloadApp')?.addEventListener('click', () => location.reload());
    $('btnClearCache')?.addEventListener('click', async () => {
      try {
        if (window.caches) {
          const keys = await caches.keys();
          await Promise.all(keys.map((key) => caches.delete(key)));
        }
        if ('serviceWorker' in navigator) {
          const regs = await navigator.serviceWorker.getRegistrations();
          await Promise.all(regs.map((reg) => reg.unregister()));
        }
        showToast('Caché limpiada, recargando…', 'success');
        window.setTimeout(() => location.reload(), 600);
      } catch {
        showToast('No se pudo limpiar la caché', 'error');
      }
    });
    $('btnInstallPwa')?.addEventListener('click', async () => {
      const prompt = state.installPrompt;
      if (!prompt) {
        showToast('Usa el menú del navegador para instalar', 'info');
        return;
      }
      prompt.prompt();
      const choice = await prompt.userChoice;
      state.installPrompt = null;
      const container = $('pwaInstallContainer');
      if (container) container.hidden = true;
      showToast(choice.outcome === 'accepted' ? 'Instalando…' : 'Instalación cancelada', 'info');
    });
  }

  function init() {
    state.isDesktop = window.matchMedia('(min-width: 1024px)').matches;
    state.pageSize = state.isDesktop ? PAGE_DESKTOP : PAGE_MOBILE;
    bindShell();
    bindSearch();
    bindCarriers();
    bindFilters();
    bindResults();
    bindConfig();
    const urlCarrier = applyUrlCarrier();
    updateCarrierUI();
    updateOnlineStatus();
    renderWeek(null);
    setView('search');
    if (state.isDesktop) {
      const sheet = $('filterSheet');
      if (sheet) sheet.hidden = false;
    }
    fetchPing();
    fetchStats();
    fetchCsvStatus();
    loadBrands();
    showState('initialState');
    if (!navigator.onLine) {
      if (!restoreLastSearch()) showState('offlineState');
    } else if (urlCarrier) {
      state.forceAll = true;
      performSearch();
    }
    $('detailBack')?.addEventListener('click', closeDetail);
    $('btnPrintMobile')?.addEventListener('click', printCurrent);
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
          .then(() => renderConfig())
          .catch(() => renderConfig());
      });
    }
  }

  window.RetailPOS = {
    state,
    setView,
    setCarrier,
    performSearch,
    renderWeek,
    formatCLP,
    formatDiscount,
    renderDetail,
    copyCode,
    showToast,
    printCurrent,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
