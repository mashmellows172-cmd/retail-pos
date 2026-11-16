"""El HTML debe actualizarse apenas se despliega una corrección.

Con la estrategia anterior (cache-first para `/`), los usuarios con la PWA
instalada seguían viendo la versión vieja del código de barras aunque el
servidor ya estuviera corregido.
"""
from pathlib import Path

SW = Path(__file__).resolve().parents[1] / "static" / "sw.js"


def test_el_service_worker_pide_el_html_actualizado():
    sw = SW.read_text(encoding="utf-8")

    # Versión nueva de caché: obliga a descartar el shell anterior.
    assert "retailpos-v2" in sw
    assert "retailpos-v1" not in sw
    # Las navegaciones van a la red primero; el caché queda para offline.
    assert "e.request.mode === 'navigate'" in sw
