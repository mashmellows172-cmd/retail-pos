"""El shell debe ser iOS, propio y sin dependencias externas."""
from pathlib import Path

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
    for needle in [
        'id="viewSearch"',
        'id="viewStats"',
        'id="viewConfig"',
        'id="searchInput"',
        'id="carrierSegmented"',
        'role="tablist"',
        'aria-selected="true"',
        'id="tabSearch"',
        'id="tabStats"',
        'id="tabConfig"',
    ]:
        assert needle in html


def test_el_css_define_el_sistema_ios():
    css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
    for token in [
        "--canvas: #F2F2F7",
        "--surface: #FFFFFF",
        "--ink: #1C1C1E",
        "--tint: #0066CC",
        "--success: #1E7A34",
        "--danger: #D70015",
        "backdrop-filter",
        "min-height: 44px",
        "prefers-reduced-motion",
    ]:
        assert token in css
    assert "-apple-system" in css
    assert "ui-monospace" in css


def test_entel_usa_azul_institucional():
    css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
    assert "--entel: #0B5BD3" in css
    assert "#C2410C" not in css
    assert "#FF6B00" not in css


def test_app_js_arranca_con_el_estado_esperado():
    js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    assert "const state = {" in js
    assert "carrier: 'TODAS'" in js
    assert "page: 1" in js
    assert "window.RetailPOS" in js
