"""El detalle debe mostrar Equipo → Plan con copiado e impresión fiel."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _js():
    return (ROOT / "static" / "app.js").read_text(encoding="utf-8")


def _html():
    return (ROOT / "templates" / "index.html").read_text(encoding="utf-8")


def test_detalle_usa_equipo_y_plan_en_orden():
    js = _js()
    assert "Código del equipo" in js
    assert "Código del plan" in js
    assert js.index("Código del equipo") < js.index("Código del plan")
    assert "Sin código de plan" in js


def test_barcode_en_pantalla_sin_texto_y_con_quiet_zone():
    js = _js()
    assert "?text=0&quiet_zone=4" in js
    assert "Código de barras del equipo" in js
    assert "Código de barras del plan" in js


def test_el_ean_se_conserva_como_texto():
    js = _js()
    assert "String(prod.ean13 || prod.plu_cod || '')" in js
    assert "Number(equipCode)" not in js


def test_dialogo_movil_es_accesible():
    html = _html()
    js = _js()
    assert 'id="detailDialog"' in html
    assert 'role="dialog"' in html and 'aria-modal="true"' in html and "aria-labelledby" in html
    # El nombre accesible coincide con el texto visible ("Volver").
    assert 'aria-label="Volver"' in html
    assert "setBackgroundInert(true)" in js
    assert "setBackgroundInert(false)" in js


def test_impresion_conserva_ids_y_usa_plan_barcode():
    html = _html()
    js = _js()
    for element_id in [
        "printTicketContainer",
        "printCarrierBrand",
        "printDescription",
        "printPlu",
        "printVigencia",
        "printDiscount",
        "printNormalPrice",
        "printFinalPrice",
        "printEanNumber",
        "printEanImg",
        "printCarrierPlan",
        "printPlanNumber",
        "printPlanImg",
        "printPluNumber",
        "printPluBarcodeImg",
        "printTimestamp",
    ]:
        assert f'id="{element_id}"' in html
    assert "document.getElementById('printPlanNumber').textContent = planCode" in js
    assert "printCurrent" in js
    # Si el producto no trae un código, la imagen anterior no debe quedar en el voucher.
    assert "img.removeAttribute('src')" in js
    assert "setBlock('printPlanBlock', Boolean(planCode))" in js
    assert 'id="printPlanBlock"' in html
