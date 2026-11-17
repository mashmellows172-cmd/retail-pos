"""Contratos aditivos de la API usados por la nueva UI.

Fijan el rango semanal derivado del Excel, los nombres originales de archivo,
el barcode sin texto embebido y el código de plan desde la columna D.
"""
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
    for op, cod, plan in [
        ("CLARO", 200028174046, 28174047),
        ("WOM", 200027762824, 27762824),
        ("ENTEL", 200027491762, 27491766),
    ]:
        ws = wb.create_sheet(op)
        ws.append(HEADERS)
        ws.append(
            [
                "APPLE",
                27537898,
                "iPhone 13 128GB Blanco",
                cod,
                plan,
                80000,
                499990,
                date(2026, 11, 11),
                date(2026, 11, 17),
            ]
        )
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
