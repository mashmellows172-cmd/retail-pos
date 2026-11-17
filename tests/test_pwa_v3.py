"""El service worker v3 debe cachear el shell y degradar a 503 sin conexión."""
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
