"""Regresiones del código de barras de planes de portabilidad.

El Excel semanal trae:
  - Columna D: "COD BARRA"  -> código que se pistolea en caja para el descuento
  - Columna E: "PLAN"       -> código interno del plan (NO es el código de barras)

Estos tests fijan el contrato para que la UI nunca vuelva a generar el código
de barras del plan desde la columna equivocada.
"""
from datetime import date
from pathlib import Path

import openpyxl
import pytest

import data_loader as dl

HEADERS = [
    "MARCA",
    "Plu_Cod",
    "Descripción",
    "COD BARRA",
    "PLAN",
    "DCTO",
    "PRECIO",
    "DESDE",
    "HASTA",
]

# (columna D - COD BARRA, columna E - PLAN, columna F - DCTO, columna G - precio)
FILAS = {
    "CLARO": (200028174046, 28174047, 80000, 499990),
    "WOM": (200027762824, 27762824, 50000, 529990),
    "ENTEL": (200027491762, 27491766, 90000, 489990),
}


def _crear_excel(path: Path) -> None:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for operadora, (cod_barra, plan, dcto, precio) in FILAS.items():
        ws = wb.create_sheet(operadora)
        ws.append(HEADERS)
        ws.append(
            [
                "APPLE",
                27537898,
                "iPhone 13 128GB Blanco",
                cod_barra,
                plan,
                dcto,
                precio,
                date(2026, 11, 11),
                date(2026, 11, 17),
            ]
        )
    wb.save(path)


@pytest.mark.parametrize("operadora", ["CLARO", "WOM", "ENTEL"])
def test_codigo_de_barras_del_plan_sale_de_la_columna_d(tmp_path, operadora):
    excel = tmp_path / "semana.xlsx"
    _crear_excel(excel)
    dl.set_excel_path(str(excel))

    filas = dl.search("", operadora=operadora, path=str(excel))
    assert len(filas) == 1

    fila = filas[0]
    cod_barra_d, plan_e, _, _ = FILAS[operadora]

    # La columna E sigue siendo el código interno del plan...
    assert fila["plan"] == str(plan_e)
    # ...y la columna D es el código de barras que se pistolea para el descuento.
    assert fila["cod_barra"] == str(cod_barra_d)
    assert fila["plan_barcode"] == str(cod_barra_d)
    assert fila["plan_barcode"] != fila["plan"]


def test_la_ui_usa_el_codigo_de_barras_de_la_columna_d():
    html = (
        Path(__file__).resolve().parents[1] / "templates" / "index.html"
    ).read_text(encoding="utf-8")

    assert "const planCode = prod.plan_barcode || '';" in html
    assert "const planCode = prod.plan || '';" not in html
    # El EAN-13 del equipo nunca debe caer en la columna D (esa es del plan).
    assert "prod.ean13 || prod.cod_barra" not in html
