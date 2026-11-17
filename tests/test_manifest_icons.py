"""El manifest debe servir iconos reales con el tema claro iOS."""
import json
from pathlib import Path

import pytest

import app as app_module  # noqa: F401  (registra la app Flask)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_manifest_iconos_existen_y_se_sirven(client):
    data = json.loads((ROOT / "static" / "manifest.json").read_text(encoding="utf-8"))
    assert data["background_color"] == "#F2F2F7"
    assert data["theme_color"] == "#F2F2F7"
    assert data["lang"] == "es-CL"
    for icon in data["icons"]:
        path = ROOT / "static" / icon["src"].removeprefix("/static/")
        assert path.is_file() and path.stat().st_size > 0
        assert client.get(icon["src"]).status_code == 200
