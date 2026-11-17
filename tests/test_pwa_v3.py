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


def test_busqueda_nueva_offline_no_muestra_la_anterior():
    js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    start = js.index("async function performSearch")
    end = js.index("function renderResults", start)
    block = js[start:end]
    assert "restoreLastSearchForCurrentQuery" in block
    offline = block[block.index("if (!navigator.onLine)") :]
    segment = offline[:600]
    assert "state.results = []" in segment
    assert "showState('offlineState')" in segment
    # Solo se restaura si la consulta y la operadora coinciden.
    assert "saved.query || ''" in js and "sameCarrier" in js


def test_assets_propios_son_network_first():
    """Un cambio de CSS/JS debe llegar aunque no se suba el nombre del caché."""
    sw = SW.read_text(encoding="utf-8")
    assert "['/static/app.css', '/static/app.js', '/manifest.json'].includes(url.pathname)" in sw
    # Navegar a /?op=CLARO sin red debe servir el shell precacheado como '/'.
    assert "caches.match(request, options)" in sw
    assert "{ ignoreSearch: true }" in sw
