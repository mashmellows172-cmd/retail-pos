"""Los uploads no deben aceptar archivos vacíos ni pisar la copia buena."""
import io

import pytest

import app as app_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_excel_invalido_se_rechaza_sin_pisar_el_bueno(client):
    before = app_module._state["excel_path"]
    res = client.post(
        "/api/upload-excel",
        data={"file": (io.BytesIO(b"esto no es un excel"), "malo.xlsx")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    assert res.get_json()["ok"] is False
    assert app_module._state["excel_path"] == before


def test_excel_con_extension_incorrecta_se_rechaza(client):
    res = client.post(
        "/api/upload-excel",
        data={"file": (io.BytesIO(b"x"), "precios.txt")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 400


def test_export_excel_sirve_el_archivo_cargado(client, tmp_path, monkeypatch):
    excel = tmp_path / "semana.xlsx"
    excel.write_bytes(b"PK\x03\x04datos")
    monkeypatch.setitem(app_module._state, "excel_path", str(excel))
    monkeypatch.setitem(app_module._state, "excel_name", "MSM W45.xlsx")

    res = client.get("/api/export-excel")

    assert res.status_code == 200
    assert res.data == b"PK\x03\x04datos"
    assert "xlsx" in res.headers.get("Content-Disposition", "")


def test_export_excel_sin_datos_responde_404(client, monkeypatch):
    monkeypatch.setitem(app_module._state, "excel_path", None)
    assert client.get("/api/export-excel").status_code == 404


def test_csv_sin_codigos_se_rechaza_sin_pisar_el_bueno(client):
    before = app_module._state["csv_path"]
    res = client.post(
        "/api/upload-csv",
        data={"file": (io.BytesIO(b"foo,bar\n1,2\n"), "vacio.csv")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    assert res.get_json()["ok"] is False
    assert app_module._state["csv_path"] == before

