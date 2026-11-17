# Rediseño de mostrador iOS — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar la UI oscura de 712 tarjetas por una experiencia de mostrador iOS con búsqueda, segmented control, detalle Equipo → Plan y PWA offline, manteniendo el barcode del plan desde la columna D (`plan_barcode`).

**Architecture:** `templates/index.html` queda como shell semántico sin framework; `static/app.css` contiene el sistema visual iOS escrito a mano; `static/app.js` contiene estado, fetch, render y comportamiento. Flask conserva los endpoints actuales y solo recibe cambios aditivos. El service worker sube a `retailpos-v3`, precachea shell, CSS, JS e iconos, y responde 503 `offline: true` cuando no hay red.

**Tech Stack:** Flask 3, pandas/openpyxl, Python 3, HTML5, CSS3 (custom properties, grid/flex, backdrop-filter), JavaScript vanilla (ES2020), service worker, pytest.

**Spec:** `docs/superpowers/specs/2026-11-16-rediseno-mostrador-design.md`

## Global Constraints

- El barcode del plan sale **siempre** de `prod.plan_barcode` (columna D, `COD BARRA`). `prod.plan` (columna E) es solo el código interno y nunca se usa como barcode.
- El código del equipo es `prod.ean13 || prod.plu_cod`. Nunca `prod.cod_barra` ni `prod.plan`.
- Orden de escaneo en el detalle: **Equipo → Plan**.
- Todo texto de interfaz va en español, con el copy exacto de la sección 18 del spec.
- Sin `cdn.tailwindcss.com`, sin Google Fonts, sin fuentes WOFF2 y sin emojis como iconos.
- `meta viewport` no incluye `maximum-scale` ni `user-scalable=no`.
- Controles interactivos de al menos 44×44 px; foco visible `2px solid #0066CC` con `outline-offset: 2px`.
- Paleta: `--canvas:#F2F2F7`, `--surface:#FFFFFF`, `--ink:#1C1C1E`, `--muted:#6C6C70`, `--tint:#0066CC`, `--success:#1E7A34`, `--danger:#D70015`. `#007AFF` solo decorativo.
- Operadoras: CLARO `#C8102E`, WOM `#6B2D8B`, ENTEL `#C2410C`, TODAS `#0066CC`.
- Tipografía UI: `-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif`. Códigos: `ui-monospace, "SF Mono", Menlo, Consolas, monospace` con `tabular-nums`.
- Paginación cliente: 40 resultados en móvil, 50 en escritorio. Solo se renderiza el layout activo.
- `matchMedia('(min-width: 1024px)')` decide tabla vs lista; al cruzar el breakpoint se re-renderiza.
- Barcode en pantalla: `/api/barcode-inline/<code>?text=0&quiet_zone=4`, fondo blanco, alt descriptivo.
- El service worker usa `retailpos-v3` y `retailpos-barcodes-v3`; el fallback API offline responde **503** con `{ "error": "Sin conexión", "offline": true }` y no cachea errores.
- Offline = shell + última búsqueda exitosa. No hay catálogo completo offline. Las búsquedas nuevas sin red muestran “Sin conexión”, no “sin resultados”.
- Se conservan todos los IDs de impresión existentes (`printTicketContainer`, `printCarrierBrand`, `printDescription`, `printPlu`, `printVigencia`, `printDiscount`, `printNormalPrice`, `printFinalPrice`, `printEanNumber`, `printEanImg`, `printCarrierPlan`, `printPlanNumber`, `printPlanImg`, `printPluNumber`, `printPluBarcodeImg`, `printTimestamp`).
- No se agregan dependencias Python ni Node. No hay paso de build.
- `python -m pytest -q` debe pasar al final de cada tarea.

## Review Focus

1. **Barcode equivocado o vacío:** un producto sin columna D debe mostrar “Sin código de plan” y no renderizar `<img>` roto ni caer a `plan`/`cod_barra`. Cubierto en Task 4.
2. **Ceros iniciales del EAN-13:** el código del equipo debe conservarse como string (`0200027537897`), no como número (`200027537897`). Cubierto en Task 4.
3. **Offline que miente:** una búsqueda nueva sin red debe mostrar “Sin conexión”, y el service worker no debe cachear respuestas 503 ni errores. Cubierto en Task 6.
4. **Desborde a 360 px:** nombres largos, contadores y el segmented control no deben provocar scroll horizontal ni texto cortado. Cubierto en Task 3 y verificado en Task 7.
5. **Excel ausente:** con `/api/ping` en `excel: null`, la app debe mostrar “No hay precios cargados” con acceso a Configuración, no un skeleton infinito. Cubierto en Task 3.

---

## File Structure

- `templates/index.html` — shell semántico: header, tres vistas, tab bar, filtros, detalle móvil, panel escritorio, toasts, banner offline y voucher de impresión.
- `static/app.css` — tokens iOS, layout responsive, componentes, estados, print.
- `static/app.js` — estado, API, render, eventos, copiado, impresión, offline.
- `static/sw.js` — cache v3, app shell, network-first, fallback 503.
- `static/manifest.json` — colores claros, iconos existentes, atajos `?op=`.
- `static/icons/icon-192.png`, `static/icons/icon-512.png`, `static/icons/icon-180.png` — iconos generados.
- `tools/make_icons.py` — generador reproducible de iconos con Pillow.
- `tests/test_api_contracts.py` — rango de fechas, nombres de archivo, barcode inline, `plan_barcode`.
- `tests/test_app_shell.py` — shell, CSS, ausencia de CDN/fuentes.
- `tests/test_search_view.py` — segmented, búsqueda, paginación, estados, URL `?op=`.
- `tests/test_detail_view.py` — Equipo → Plan, barcodes, dialog, copiado, impresión.
- `tests/test_stats_config.py` — semana derivada, stats, configuración, nombres de archivo.
- `tests/test_pwa_v3.py` — cache v3, app shell, fallback 503.
- `tests/test_manifest_icons.py` — manifest e iconos servidos.
- `tests/test_plan_barcode.py` — se actualiza para leer también `static/app.js`.
- `HANDOFF.md` — se actualiza al final.

---

### Task 1: Contratos aditivos de API

**Files:**
- Modify: `data_loader.py`
- Modify: `app.py`
- Test: `tests/test_api_contracts.py`

**Interfaces:**
- Consumes: `data_loader.load_all(path)` y `_to_records` existentes; `_state["excel_path"]`, `_state["csv_path"]`.
- Produces:
  - `data_loader.business_week(d: date) -> int`
  - `data_loader.get_date_range(path: str | None = None) -> dict` con `{"desde": "YYYY-MM-DD", "hasta": "YYYY-MM-DD", "semana": int}` o `{}` si no hay datos.
  - `/api/stats` agrega la clave `_rango` con ese dict.
  - `/api/ping` agrega `excel_name` y `csv_name` (basename o `null`).
  - `/api/barcode-inline/<code>` acepta `?text=0` y `?quiet_zone=<float>`.
  - `_state["excel_name"]` y `_state["csv_name"]` se actualizan al iniciar, en `set_excel`, `upload_excel` y `upload_csv`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_api_contracts.py
from datetime import date
from pathlib import Path

import openpyxl
import pytest

import app as app_module
import data_loader as dl

HEADERS = ["MARCA", "Plu_Cod", "Descripción", "COD BARRA", "PLAN", "DCTO", "PRECIO", "DESDE", "HASTA"]


def _excel(tmp_path: Path) -> Path:
    path = tmp_path / "semana.xlsx"
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for op, cod, plan in [("CLARO", 200028174046, 28174047), ("WOM", 200027762824, 27762824), ("ENTEL", 200027491762, 27491766)]:
        ws = wb.create_sheet(op)
        ws.append(HEADERS)
        ws.append(["APPLE", 27537898, "iPhone 13 128GB Blanco", cod, plan, 80000, 499990, date(2026, 11, 11), date(2026, 11, 17)])
    wb.save(path)
    return path


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_business_week_usa_la_convencion_del_archivo():
    assert dl.business_week(date(2026, 11, 11)) == 45
    assert dl.business_week(date(2026, 11, 17)) == 46


def test_stats_incluye_rango_y_semana(tmp_path, client, monkeypatch):
    excel = _excel(tmp_path)
    monkeypatch.setitem(app_module._state, "excel_path", str(excel))
    dl.set_excel_path(str(excel))
    data = client.get("/api/stats").get_json()
    assert data["_rango"] == {"desde": "2026-11-11", "hasta": "2026-11-17", "semana": 45}
    assert data["CLARO"]["total"] == 1


def test_ping_devuelve_nombres_originales(client, monkeypatch):
    monkeypatch.setitem(app_module._state, "excel_name", "MSM W45 (11.11 - 17.11) TIENDAS.xlsx")
    monkeypatch.setitem(app_module._state, "csv_name", "OUT-33644917.csv")
    data = client.get("/api/ping").get_json()
    assert data["excel_name"] == "MSM W45 (11.11 - 17.11) TIENDAS.xlsx"
    assert data["csv_name"] == "OUT-33644917.csv"


def test_barcode_inline_acepta_text_y_quiet_zone(client, monkeypatch):
    import barcode
    calls = {}

    class Fake:
        def write(self, buf, options):
            calls.update(options)
            buf.write(b"<svg/>")

    def fake_get(name, code, writer=None):
        calls["name"] = name
        calls["code"] = code
        return Fake()

    monkeypatch.setattr(barcode, "get", fake_get)
    res = client.get("/api/barcode-inline/200028174046?text=0&quiet_zone=4")
    assert res.status_code == 200
    assert calls["write_text"] is False
    assert calls["quiet_zone"] == 4.0


def test_search_expone_plan_barcode_distinto_de_plan(tmp_path, client, monkeypatch):
    excel = _excel(tmp_path)
    monkeypatch.setitem(app_module._state, "excel_path", str(excel))
    dl.set_excel_path(str(excel))
    row = client.get("/api/search?q=27537898").get_json()[0]
    assert row["plan_barcode"] == "200028174046"
    assert row["plan"] == "28174047"
    assert row["plan_barcode"] != row["plan"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_api_contracts.py -q`
Expected: FAIL con `AttributeError: module 'data_loader' has no attribute 'business_week'`.

- [ ] **Step 3: Implement the contracts**

En `data_loader.py`:

- `business_week(d)` devuelve `math.ceil(d.timetuple().tm_yday / 7)`.
- `get_date_range(path=None)` carga `load_all(path)`, junta `desde`/`hasta` no nulos, toma mínimo/máximo y devuelve strings ISO con `semana=business_week(desde)`. Si no hay datos, `{}`.
- No cambies `get_stats` ni `_to_records`.

En `app.py`:

- Agrega `_basename(path)` y usa `_state["excel_name"]` / `_state["csv_name"]` en el estado inicial, `set_excel`, `upload_excel` y `upload_csv`.
- `/api/stats`: `payload = dl.get_stats(path); payload["_rango"] = dl.get_date_range(path); return jsonify(payload)`. Sin path, `{"_rango": {}}`.
- `/api/ping`: agrega `excel_name` y `csv_name` desde `_state`.
- `/api/barcode-inline`: parsea `text = request.args.get("text", "1") != "0"` y `quiet_zone`; usa `float` con fallback `2.5` y limita a `1.0..10.0`; pasa `write_text=text`, `quiet_zone=quiet_zone` a `code128.write`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_api_contracts.py tests/test_plan_barcode.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app.py data_loader.py tests/test_api_contracts.py
git commit -m "feat(api): expone rango semanal, nombres de archivo y barcode sin texto"
```

---

### Task 2: Shell iOS, tokens y CSS propio

**Files:**
- Create: `static/app.css`
- Create: `static/app.js`
- Rewrite: `templates/index.html`
- Test: `tests/test_app_shell.py`

**Interfaces:**
- Consumes: URLs `/static/app.css`, `/static/app.js`, `/manifest.json`.
- Produces: shell con `#viewSearch`, `#viewStats`, `#viewConfig`, `#searchInput`, `#carrierSegmented`, `#tabSearch/#tabStats/#tabConfig`, `#offlineBanner`, `#toastContainer`, `#printTicketContainer`.
- `static/app.js` expone `window.RetailPOS = { state, setView, renderWeek }` para verificación manual; el resto queda en un IIFE.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_app_shell.py
from pathlib import Path

import app as app_module

ROOT = Path(__file__).resolve().parents[1]


def test_el_shell_no_usa_cdn_ni_fuentes_externas():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    assert "cdn.tailwindcss.com" not in html
    assert "fonts.googleapis.com" not in html
    assert "fonts.gstatic.com" not in html
    assert "maximum-scale" not in html
    assert "user-scalable=no" not in html
    assert "/static/app.css" in html
    assert "/static/app.js" in html


def test_el_shell_tiene_las_tres_vistas_y_el_segmented():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    for needle in ['id="viewSearch"', 'id="viewStats"', 'id="viewConfig"', 'id="searchInput"', 'id="carrierSegmented"', 'role="tablist"', 'aria-selected="true"']:
        assert needle in html
    assert 'id="tabSearch"' in html and 'id="tabStats"' in html and 'id="tabConfig"' in html


def test_el_css_define_el_sistema_ios():
    css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
    for token in ["--canvas: #F2F2F7", "--surface: #FFFFFF", "--ink: #1C1C1E", "--tint: #0066CC", "--success: #1E7A34", "--danger: #D70015", "backdrop-filter", "min-height: 44px", "prefers-reduced-motion"]:
        assert token in css
    assert "-apple-system" in css and "ui-monospace" in css


def test_app_js_arranca_con_el_estado_esperado():
    js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    assert "const state = {" in js
    assert "carrier: 'TODAS'" in js
    assert "page: 1" in js
    assert "window.RetailPOS" in js
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_app_shell.py -q`
Expected: FAIL porque `static/app.css` no existe.

- [ ] **Step 3: Create the shell, CSS and JS bootstrap**

- `templates/index.html`: `<html lang="es">`; `<meta name="theme-color" content="#F2F2F7">`; `<link rel="manifest" href="/manifest.json">`; `<link rel="apple-touch-icon" href="/static/icons/icon-180.png">`; `<link rel="stylesheet" href="/static/app.css">`; `<script src="/static/app.js" defer></script>`.
- Header: marca “RetailPOS”, `#headerWeek` con “Sin precios cargados”, `#connectionPill` con punto y `#connectionText` “En línea”.
- Tres `<section class="view">`: `#viewSearch` con búsqueda, segmented, filtros, resultados y detalle; `#viewStats` con large title y `#statsGrid`; `#viewConfig` con large title, filas Excel/CSV y `<details>` Avanzado.
- Tab bar inferior con tres `<button class="tabbar-item">` y `aria-current="page"`.
- Voucher de impresión con todos los IDs listados en Global Constraints.
- `static/app.js`: IIFE con `state = {carrier:'TODAS', query:'', brand:'', minDcto:'', maxPrice:'', results:[], stats:{}, selected:null, view:'search', page:1, pageSize:40, loading:false, hasData:null, forceAll:false, isDesktop:false, lastFocus:null}`; `setView(view)`, `renderWeek(range)`, `init()`; `window.RetailPOS = {state, setView, renderWeek}`.
- `static/app.css`: tokens exactos; reset; `body` canvas e ink; header translúcido; segmented; search field; groups; result rows; detail; tabbar; sheets; stats; config; toast; skeleton; print; media queries 1024 px; `@media print` que muestra solo `#printTicketContainer`; `@media (prefers-reduced-motion: reduce)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_app_shell.py -q`
Expected: PASS.

- [ ] **Step 5: Open `/` and verify the shell**

Run local Flask on `127.0.0.1:5050`, open `/`, verify: canvas claro, header translúcido, tres tabs, segmented de 4, sin scroll horizontal a 390 px. No se exige comportamiento aún.

- [ ] **Step 6: Commit**

```bash
git add templates/index.html static/app.css static/app.js tests/test_app_shell.py
git commit -m "feat(ui): reemplaza tailwind por shell iOS propio"
```

---

### Task 3: Búsqueda, operadora, filtros y resultados

**Files:**
- Modify: `static/app.js`
- Modify: `templates/index.html`
- Modify: `static/app.css`
- Test: `tests/test_search_view.py`

**Interfaces:**
- Consumes: `GET /api/search?q&op&marca&min_dcto&max_precio`, `GET /api/brands?operadora=`, `GET /api/ping`.
- Produces:
  - `setCarrier(op: 'TODAS'|'CLARO'|'WOM'|'ENTEL')`
  - `performSearch(resetPage = true)`
  - `renderResults()` que llama a `renderMobileList()` **o** `renderDesktopTable()`, nunca ambas.
  - `state.pageSize = state.isDesktop ? 50 : 40`.
  - `localStorage['retailpos:lastSearch:v1'] = JSON.stringify({query, carrier, results, savedAt})` tras una búsqueda exitosa.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_search_view.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _source():
    return (ROOT / "templates" / "index.html").read_text(encoding="utf-8") + (ROOT / "static" / "app.js").read_text(encoding="utf-8")


def test_segmented_control_semantico_y_url_op():
    js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    assert "new URLSearchParams(location.search).get('op')" in js
    assert "aria-selected" in js
    assert "data-carrier" in (ROOT / "templates" / "index.html").read_text(encoding="utf-8")


def test_debounce_paginacion_y_layout_unico():
    js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    assert "}, 300);" in js
    assert "state.isDesktop ? 50 : 40" in js
    assert "matchMedia('(min-width: 1024px)')" in js
    assert "renderMobileList()" in js and "renderDesktopTable()" in js
    assert "state.view !== 'search'" in js


def test_estado_inicial_no_consulta_el_catalogo():
    js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    assert "if (!state.query && !state.brand && !state.minDcto && !state.maxPrice && !state.forceAll)" in js
    assert "Escanea o busca un equipo" in (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    assert "Ver todo el catálogo" in (ROOT / "templates" / "index.html").read_text(encoding="utf-8")


def test_estados_sin_datos_sin_resultados_y_offline():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    assert "No hay precios cargados" in html
    assert "No encontramos ese producto" in html
    assert "Limpiar filtros" in html
    assert "No pudimos conectar" in html
    assert "api/ping" in js and "data.excel" in js
    assert "error.offline" in js


def test_nombres_largos_no_desbordan():
    css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
    assert "text-overflow: ellipsis" in css
    assert "min-width: 0" in css
    assert "overflow-wrap: anywhere" in css
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_search_view.py -q`
Expected: FAIL en `test_segmented_control_semantico_y_url_op`.

- [ ] **Step 3: Implement search and results**

- Segmentos como `<button role="tab" data-carrier="TODAS|CLARO|WOM|ENTEL" aria-selected>` dentro de `#carrierSegmented role="tablist"`; conteos en `<span class="seg-count">`.
- `init()` lee `?op=`; si es válido, `state.carrier` y `aria-selected` se actualizan antes de la primera búsqueda. `setCarrier` resetea `page=1` y consulta.
- Búsqueda: `input` con debounce 300 ms; Enter inmediato; tras la respuesta, el foco vuelve a `#searchInput`; `forceAll` solo para “Ver todo el catálogo”.
- `performSearch` arma `URLSearchParams` con `q, op (si no es TODAS), marca, min_dcto, max_precio`; `fetch('/api/search?...')`; en éxito guarda `lastSearch`; en 503/`offline` restaura la última búsqueda o muestra error offline; en error de red muestra “No pudimos conectar” + “Reintentar”.
- `renderResults` actualiza contador `aria-live="polite"` con “N de M productos”; corta `state.results.slice(0, state.page * state.pageSize)`; `renderMobileList` produce `<button class="result-row" data-index>` con operadora, marca, descripción, PLU, descuento y precio; `renderDesktopTable` produce `<tr>` con `<button data-action="detail" data-index>` “Ver códigos”.
- `#loadMore` agrega una página; desaparece si no hay más; no reemplaza el foco.
- Skeleton de 3 filas mientras `state.loading`; estados inicial/sin datos/sin resultados según spec.
- Filtros móvil: `#filterSheet role="dialog" aria-modal="true" aria-labelledby="filterTitle"` con grabber, backdrop, Escape, X de 44 px; escritorio: `.filters-inline` visible solo en ≥1024 px. Ambos leen los mismos inputs.
- CSS: `overflow-wrap:anywhere` en descripciones, `text-overflow:ellipsis` en títulos de una línea, `min-width:0` en grids/flex.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_search_view.py tests/test_app_shell.py -q`
Expected: PASS.

- [ ] **Step 5: Verify in browser**

Abre `/` con datos locales. Verifica: estado inicial sin 712 filas; `/?op=CLARO` activa Claro; búsqueda “iphone 13” lista 40 filas; “Cargar más” agrega 40; a 360 px no hay scroll horizontal; a 1024 px aparece la tabla y no la lista móvil.

- [ ] **Step 6: Commit**

```bash
git add templates/index.html static/app.js static/app.css tests/test_search_view.py
git commit -m "feat(ui): agrega busqueda, operadora y resultados paginados"
```

---

### Task 4: Detalle Equipo → Plan, copiado e impresión

**Files:**
- Modify: `static/app.js`
- Modify: `templates/index.html`
- Modify: `static/app.css`
- Modify: `tests/test_plan_barcode.py`
- Test: `tests/test_detail_view.py`

**Interfaces:**
- Consumes: producto de `state.results`, `plan_barcode`, `ean13`, `plu_cod`, `/api/barcode-inline`.
- Produces:
  - `openDetail(index)` / `closeDetail()` con restauración de foco.
  - `renderDetail(container, prod)` compartido por `#detailDialog` (móvil) y `#desktopDetail` (escritorio).
  - `equipCode = String(prod.ean13 || prod.plu_cod || '')`
  - `planCode = String(prod.plan_barcode || '')` — esta línea debe existir literalmente como `const planCode = prod.plan_barcode || '';`
  - `printCurrent()` con `window.print()`.

- [ ] **Step 1: Update the existing barcode test and write the detail tests**

```python
# tests/test_plan_barcode.py — reemplaza test_la_ui_usa_el_codigo_de_barras_de_la_columna_d
def test_la_ui_usa_el_codigo_de_barras_de_la_columna_d():
    root = Path(__file__).resolve().parents[1]
    source = (root / "templates" / "index.html").read_text(encoding="utf-8")
    source += (root / "static" / "app.js").read_text(encoding="utf-8")
    assert "const planCode = prod.plan_barcode || '';" in source
    assert "const planCode = prod.plan || '';" not in source
    assert "prod.ean13 || prod.cod_barra" not in source
    assert "prod.ean13 || prod.plu_cod" in source
```

```python
# tests/test_detail_view.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _js():
    return (ROOT / "static" / "app.js").read_text(encoding="utf-8")


def test_detalle_usa_equipo_y_plan_en_orden():
    js = _js()
    assert "Código del equipo" in js
    assert "Código del plan" in js
    assert js.index("Código del equipo") < js.index("Código del plan")
    assert "Sin código de plan" in js


def test_barcode_en_pantalla_sin_texto_y_con_quiet_zone():
    js = _js()
    assert "?text=0&quiet_zone=4" in js
    assert "Código de barras del equipo" in js
    assert "Código de barras del plan" in js


def test_el_ean_se_conserva_como_texto():
    js = _js()
    assert "String(prod.ean13 || prod.plu_cod || '')" in js
    assert "Number(equipCode)" not in js


def test_dialogo_movil_es_accesible():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    assert 'id="detailDialog"' in html
    assert 'role="dialog"' in html and 'aria-modal="true"' in html and "aria-labelledby" in html
    assert 'aria-label="Cerrar"' in html


def test_impresion_conserva_ids_y_usa_plan_barcode():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    js = _js()
    for element_id in ["printTicketContainer", "printCarrierBrand", "printDescription", "printPlu", "printVigencia", "printDiscount", "printNormalPrice", "printFinalPrice", "printEanNumber", "printEanImg", "printCarrierPlan", "printPlanNumber", "printPlanImg", "printPluNumber", "printPluBarcodeImg", "printTimestamp"]:
        assert f'id="{element_id}"' in html
    assert "document.getElementById('printPlanNumber').textContent = planCode" in js
    assert "printCurrent" in js
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_plan_barcode.py tests/test_detail_view.py -q`
Expected: FAIL en `Código del equipo`.

- [ ] **Step 3: Implement detail, copy and print**

- Móvil: `#detailDialog` a pantalla completa, `role="dialog" aria-modal="true" aria-labelledby="detailTitle"`; al abrir guarda `state.lastFocus`, enfoca “Volver”, aplica `document.querySelector('main').inert = true`, cierra con Escape/backdrop/Volver y restaura foco.
- Escritorio: `#desktopDetail` sticky, sin modal; se actualiza con el primer resultado si no hay selección y el producto sigue en la página.
- `renderDetail(container, prod)`:
  - Resumen: descuento `-$80.000`, precio final, precio normal, PLU, vigencia.
  - Sección “Códigos para escanear”.
  - Tarjeta 1: “Código del equipo”; `<img src="/api/barcode-inline/${equipCode}?text=0&quiet_zone=4" alt="Código de barras del equipo" loading="lazy" decoding="async">`; número en `<button data-copy="equip">`; texto “Copiar código”.
  - Tarjeta 2: “Código del plan · CLARO”; mismo tratamiento con `planCode`; si `planCode === ''`, muestra “Sin código de plan”, oculta la imagen y deshabilita copiar.
  - `alt` del plan: `Código de barras del plan ${prod.operadora}`.
  - Orden DOM Equipo → Plan.
- Copiado: `navigator.clipboard.writeText`, toast `role="status"` “Código copiado”; error `role="alert"` “No se pudo copiar”; feedback del botón “Copiado” por 1.5 s.
- `printCurrent()` llena los IDs, usa `planCode`, espera `Promise.all` de las tres imágenes con timeout de 1500 ms y llama `window.print()`.
- CSS: en 390×844 las dos tarjetas deben caber sin scroll interno; `.barcode-box img { width:100%; height:76px; object-fit:fill; }`; footer fijo de 64 px + `env(safe-area-inset-bottom)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_plan_barcode.py tests/test_detail_view.py -q`
Expected: PASS.

- [ ] **Step 5: Verify barcode and keyboard behavior**

Abre un iPhone 13 CLARO local. Verifica en 390×844: ambos barcodes completos sin scroll, `0200027537897` (equipo) y `200028174046` (plan). Copia ambos, imprime y confirma que el voucher usa `200028174046`. Recorre todo con Tab/Enter/Escape.

- [ ] **Step 6: Commit**

```bash
git add templates/index.html static/app.js static/app.css tests/test_plan_barcode.py tests/test_detail_view.py
git commit -m "feat(ui): muestra codigos equipo y plan con copiado e impresion"
```

---

### Task 5: Stats, Configuración y semana derivada

**Files:**
- Modify: `static/app.js`
- Modify: `templates/index.html`
- Modify: `static/app.css`
- Test: `tests/test_stats_config.py`

**Interfaces:**
- Consumes: `/api/stats` con `_rango`, `/api/ping` con `excel_name`/`csv_name`, `/api/upload-excel`, `/api/upload-csv`, `/api/csv-status`.
- Produces:
  - `renderWeek(range)` muestra `Semana ${range.semana} · ${formatRange(range.desde, range.hasta)}` o “Sin precios cargados”.
  - `renderStats(stats)` ignora claves que empiezan con `_`.
  - `renderConfig(ping)` muestra nombres de archivo y estados.
  - `uploadExcel(file)` y `uploadCsv(file)` refrescan ping, stats y búsqueda.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_stats_config.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _js():
    return (ROOT / "static" / "app.js").read_text(encoding="utf-8")


def _html():
    return (ROOT / "templates" / "index.html").read_text(encoding="utf-8")


def test_semana_no_esta_hardcodeada():
    js = _js()
    assert "stats._rango" in js
    assert "range.semana" in js
    assert "Semana 45" not in js
    assert "11-17 Nov" not in js


def test_stats_ignora_la_clave_de_rango():
    js = _js()
    assert "key.startsWith('_')" in js
    assert "id=\"statsGrid\"" in _html()
    assert "Máx. descuento" in _html()


def test_config_muestra_nombres_y_estado():
    html = _html()
    js = _js()
    for needle in ['id="configExcelName"', 'id="configCsvName"', 'id="excelFileInput"', 'id="csvFileInput"', 'id="btnInstallPwa"']:
        assert needle in html
    assert "data.excel_name" in js
    assert "data.csv_name" in js
    assert "Uso administrativo" in html


def test_config_refresca_todo_despues_de_subir():
    js = _js()
    assert "await fetchPing()" in js
    assert "await fetchStats()" in js
    assert "performSearch()" in js
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_stats_config.py -q`
Expected: FAIL en `stats._rango`.

- [ ] **Step 3: Implement Stats and Config**

- `renderWeek`: usa `_rango`; formatea el rango con meses abreviados en español (`11–17 nov`) sin depender de locale del navegador; si falta `_rango` o está vacío, “Sin precios cargados”.
- `renderStats`: recorre `Object.entries(stats)`, salta `key.startsWith('_')`, muestra un grupo blanco por operadora con círculo de 28 px, total 34 px, marcas, máximo descuento y rango de precios; “Ver productos” es un `<button>` de 44 px que llama `setCarrier(op)` y `setView('search')`. Skeleton de 3 grupos; error con “Reintentar”.
- `renderConfig`: filas agrupadas para Excel y CSV; iconos cuadrados de 29 px; estado con `excel_name`/`csv_name` o “Sin archivo”; botones de 50 px; spinner; aviso “Uso administrativo” como footnote; `<details>` Avanzado con versión, estado SW, modo offline, “Limpiar caché” y “Recargar”.
- Uploads: `input type=file` oculto + botón que lo activa; `FormData` a `/api/upload-excel` o `/api/upload-csv`; en éxito toast y refresco; en error toast `role="alert"`. Conserva el nombre original que devuelve el servidor.
- `init()` en paralelo: `fetchPing()`, `fetchStats()`, `fetchCsvStatus()`, `loadBrands()`; no lanza búsqueda de catálogo sin filtros.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_stats_config.py -q`
Expected: PASS.

- [ ] **Step 5: Verify with real data**

Abre Stats: 3 grupos, semana 45, sin “Semana 45” hardcodeada en el JS. En Config verifica el nombre del Excel real y el CSV. Sube un Excel de prueba y confirma que header, stats y búsqueda se actualizan sin recargar.

- [ ] **Step 6: Commit**

```bash
git add templates/index.html static/app.js static/app.css tests/test_stats_config.py
git commit -m "feat(ui): agrega estadisticas y configuracion iOS"
```

---

### Task 6: PWA v3, manifest, iconos y offline

**Files:**
- Modify: `static/sw.js`
- Modify: `static/manifest.json`
- Modify: `templates/index.html`
- Modify: `static/app.js`
- Create: `tools/make_icons.py`
- Create: `static/icons/icon-192.png`, `static/icons/icon-512.png`, `static/icons/icon-180.png`
- Create: `tests/test_pwa_v3.py`
- Create: `tests/test_manifest_icons.py`
- Delete/rewrite: `tests/test_pwa_update.py` → se reemplaza por `tests/test_pwa_v3.py`

**Interfaces:**
- Consumes: `static/app.css`, `static/app.js`, `static/icons/*`, `localStorage['retailpos:lastSearch:v1']`.
- Produces:
  - `CACHE_NAME='retailpos-v3'`, `BARCODE_CACHE='retailpos-barcodes-v3'`.
  - `APP_SHELL=['/','/static/app.css','/static/app.js','/manifest.json','/static/icons/icon-192.png','/static/icons/icon-512.png']`.
  - Fallback API: `new Response(..., {status:503, headers:{'Content-Type':'application/json'}})`.
  - Manifest: `background_color` y `theme_color` `#F2F2F7`, `lang` `es-CL`, iconos 192/512 existentes, atajos `?op=`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pwa_v3.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SW = ROOT / "static" / "sw.js"


def test_cache_v3_y_app_shell_completo():
    sw = SW.read_text(encoding="utf-8")
    assert "retailpos-v3" in sw
    assert "retailpos-barcodes-v3" in sw
    assert "retailpos-v2" not in sw
    for asset in ["/static/app.css", "/static/app.js", "/manifest.json", "/static/icons/icon-192.png", "/static/icons/icon-512.png"]:
        assert asset in sw
    assert "e.request.mode === 'navigate'" in sw


def test_fallback_api_offline_es_503_y_no_cachea_errores():
    sw = SW.read_text(encoding="utf-8")
    assert "offline: true" in sw
    assert "status: 503" in sw
    assert "if (response.ok)" in sw


def test_app_js_conserva_la_ultima_busqueda():
    js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    assert "retailpos:lastSearch:v1" in js
    assert "localStorage.setItem" in js
    assert "localStorage.getItem" in js
    assert "Sin conexión — mostrando datos guardados" in js
```

```python
# tests/test_manifest_icons.py
import json
from pathlib import Path

import app as app_module

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_iconos_existen_y_se_sirven(client):
    data = json.loads((ROOT / "static" / "manifest.json").read_text(encoding="utf-8"))
    assert data["background_color"] == "#F2F2F7"
    assert data["theme_color"] == "#F2F2F7"
    assert data["lang"] == "es-CL"
    for icon in data["icons"]:
        path = ROOT / "static" / icon["src"].removeprefix("/static/")
        assert path.is_file() and path.stat().st_size > 0
        assert client.get(icon["src"]).status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pwa_v3.py tests/test_manifest_icons.py -q`
Expected: FAIL porque `retailpos-v3` no existe.

- [ ] **Step 3: Implement PWA v3 and offline behavior**

- `static/sw.js`: sube versiones; `APP_SHELL` exacto; en `networkFirst`, solo `cache.put` si `response.ok`; en `catch`, devuelve 503 JSON con `offline:true`. Mantén cache-first para `/api/barcode-inline/` y assets.
- `static/manifest.json`: colores y lang; conserva atajos; `icons` con `purpose:"any maskable"`; agrega `apple-touch-icon` 180 en HTML.
- `tools/make_icons.py`: genera 192, 512 y 180 con Pillow: fondo `#0066CC`, cinco barras blancas centradas, contenido dentro del 80% central para maskable; sin texto. Ejecuta `python tools/make_icons.py`.
- `static/app.js`:
  - `saveLastSearch()` y `loadLastSearch()` con la clave exacta.
  - En `init()`, si `!navigator.onLine`, restaura la última búsqueda y muestra banner “Sin conexión — mostrando datos guardados”; si no hay, muestra “Sin conexión” + “Reintentar”.
  - En respuestas 503 o `payload.offline`, no muestra “sin resultados”; muestra estado offline y conserva `state.results` si existían.
  - `online`/`offline` listeners actualizan pill y banner sin recargar.
- No precaches `/api/*` ni el Excel.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pwa_v3.py tests/test_manifest_icons.py -q`
Expected: PASS.

- [ ] **Step 5: Verify offline and installation**

En Chrome: carga una búsqueda, DevTools → Application → Service Workers → Offline, recarga. Debe abrir el shell y mostrar la última búsqueda con banner. Intenta una búsqueda nueva: “Sin conexión”, no “No encontramos ese producto”. Revisa que `sw.js` activo sea v3 y que los iconos respondan 200.

- [ ] **Step 6: Commit**

```bash
git add static/sw.js static/manifest.json static/app.js templates/index.html tools/make_icons.py static/icons tests/test_pwa_v3.py tests/test_manifest_icons.py
git rm tests/test_pwa_update.py
git commit -m "feat(pwa): sube cache v3 y agrega offline de ultima busqueda"
```

---

### Task 7: Accesibilidad, rendimiento y verificación final

**Files:**
- Modify: `static/app.css`, `static/app.js`, `templates/index.html` solo si la verificación encuentra fallos.
- Modify: `HANDOFF.md`
- Test: suite completa + verificación manual.

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: entrega verificada; `HANDOFF.md` con cache v3, archivos nuevos y recordatorio de re-subir el Excel en Vercel.

- [ ] **Step 1: Run the full suite**

Run: `python -m pytest -q`
Expected: todos los tests pasan; ninguno referencia `retailpos-v2`, `cdn.tailwindcss.com` ni Google Fonts.

- [ ] **Step 2: Check DOM, controls and contrast**

Run local con datos reales y en DevTools:

- Con 40 resultados, `document.querySelectorAll('*').length < 2500`.
- `[...document.querySelectorAll('button,a,input,select')].filter(el => { const r = el.getBoundingClientRect(); return r.width && (r.width < 44 || r.height < 44); }).length === 0` (excepto enlaces de texto fuera de flujo, si los hay, justificados).
- Ningún `<div onclick>` ni `<tr onclick>` en el HTML/JS.
- Lighthouse Accessibility ≥ 95 y cero fallos de contraste.

- [ ] **Step 3: Check responsive and keyboard**

Anchos 360, 390, 430, 768, 1024 y 1440 px: sin `document.documentElement.scrollWidth > innerWidth`. En 390×844 el detalle muestra Equipo → Plan sin scroll. Recorre con Tab, Enter y Escape: buscar, filtrar, abrir, copiar, imprimir y cerrar sin mouse. Verifica zoom móvil.

- [ ] **Step 4: Check barcode, print and offline with real data**

- Escanea con hardware el barcode del equipo y el del plan desde la pantalla.
- Imprime el voucher: tres códigos, plan `200028174046` para CLARO.
- Repite offline: shell + última búsqueda, sin resultados falsos.
- Verifica `/?op=WOM` y `/?op=ENTEL`.

- [ ] **Step 5: Update HANDOFF.md**

Incluye: nueva arquitectura (`index.html` + `app.css` + `app.js`), cache `retailpos-v3`, comandos de test, generación de iconos, endpoints aditivos (`_rango`, `excel_name`, `csv_name`, `text`, `quiet_zone`) y la nota: **en Vercel hay que volver a subir el Excel después de cada despliegue porque el filesystem es efímero**.

- [ ] **Step 6: Final commit**

```bash
git add HANDOFF.md static/app.css static/app.js templates/index.html
git commit -m "chore: verificacion final de accesibilidad, responsive y offline"
```

---

## Execution Notes

- No ejecutes Task 2 sobre una rama con cambios sin commitear; la reescritura de `templates/index.html` es total.
- Si el ejecutor encuentra un test viejo que depende del markup anterior, actualízalo a una aserción estructural; conserva siempre `plan_barcode`, network-first y los IDs de impresión.
- El mockup de referencia es `docs/superpowers/specs/mockups/retailpos-mostrador.html`; ante una duda visual, cópialo, no inventes un componente nuevo.
- No agregues búsqueda offline completa, IndexedDB de catálogo ni sincronización en background: están fuera de alcance.
