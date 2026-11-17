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
