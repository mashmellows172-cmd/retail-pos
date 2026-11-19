"""Persistencia opcional en Vercel Blob (sin red en los tests)."""
import json

import storage


def test_inactivo_sin_token(monkeypatch):
    monkeypatch.delenv("BLOB_READ_WRITE_TOKEN", raising=False)
    assert storage.enabled() is False
    assert storage.save("excel", "semana.xlsx", b"data") is None
    assert storage.latest("excel") is None
    assert storage.restore("excel", "destino.xlsx") is None


def test_save_usa_hash_y_nombre_original(monkeypatch):
    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "token")
    calls = []

    def fake_request(url, method="GET", data=None, headers=None, timeout=30):
        calls.append({"url": url, "method": method, "data": data, "headers": headers})
        return b"{}"

    monkeypatch.setattr(storage, "_request", fake_request)
    pathname = storage.save("excel", "MSM W45 (11.11 - 17.11) TIENDAS.xlsx", b"contenido")

    assert pathname.startswith("retailpos/excel-")
    assert pathname.endswith(".xlsx")
    assert "MSM_W45" in pathname
    assert calls[0]["method"] == "PUT"
    assert calls[0]["data"] == b"contenido"
    assert calls[0]["headers"]["x-vercel-blob-access"] == "private"


def test_latest_elige_el_mas_reciente(monkeypatch):
    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "token")
    payload = {
        "blobs": [
            {"pathname": "retailpos/excel-viejo.xlsx", "uploadedAt": "2026-11-01T00:00:00Z", "url": "u1"},
            {"pathname": "retailpos/excel-nuevo.xlsx", "uploadedAt": "2026-11-18T00:00:00Z", "url": "u2"},
        ]
    }
    monkeypatch.setattr(storage, "_request", lambda *args, **kwargs: json.dumps(payload).encode())

    item = storage.latest("excel")
    assert item["pathname"] == "retailpos/excel-nuevo.xlsx"


def test_nombre_desde_pathname():
    assert storage.name_from_pathname("retailpos/excel-abc123-MSM_W45.xlsx", "x") == "MSM_W45.xlsx"
    assert storage.name_from_pathname("", "respaldo.xlsx") == "respaldo.xlsx"
