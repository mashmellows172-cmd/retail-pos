"""La búsqueda debe ser directa, paginada y usable sin catálogo completo."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _js():
    return (ROOT / "static" / "app.js").read_text(encoding="utf-8")


def _html():
    return (ROOT / "templates" / "index.html").read_text(encoding="utf-8")


def test_segmented_control_semantico_y_url_op():
    js = _js()
    assert "new URLSearchParams(location.search).get('op')" in js
    assert "aria-selected" in js
    assert "data-carrier" in _html()


def test_debounce_paginacion_y_layout_unico():
    js = _js()
    assert "}, 300);" in js
    assert "state.isDesktop ? 50 : 40" in js
    assert "matchMedia('(min-width: 1024px)')" in js
    assert "renderMobileList()" in js and "renderDesktopTable()" in js
    assert "state.view !== 'search'" in js


def test_estado_inicial_no_consulta_el_catalogo():
    js = _js()
    assert "if (!state.query && !state.brand && !state.minDcto && !state.maxPrice && !state.forceAll)" in js
    assert "Escanea o busca un equipo" in _html()
    assert "Ver todo el catálogo" in _html()


def test_estados_sin_datos_sin_resultados_y_offline():
    html = _html()
    js = _js()
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
