"""Semana derivada, estadísticas y configuración de fuentes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _js():
    return (ROOT / "static" / "app.js").read_text(encoding="utf-8")


def _html():
    return (ROOT / "templates" / "index.html").read_text(encoding="utf-8")


def test_semana_no_esta_hardcodeada():
    js = _js()
    assert "stats._rango" in js
    assert "range.semana" in js
    assert "Semana 45" not in js
    assert "11-17 Nov" not in js


def test_stats_ignora_la_clave_de_rango():
    js = _js()
    assert "key.startsWith('_')" in js
    assert 'id="statsGrid"' in _html()
    assert "Máx. descuento" in _html()


def test_config_muestra_nombres_y_estado():
    html = _html()
    js = _js()
    for needle in ['id="configExcelName"', 'id="configCsvName"', 'id="excelFileInput"', 'id="csvFileInput"', 'id="btnInstallPwa"']:
        assert needle in html
    assert "data.excel_name" in js
    assert "data.csv_name" in js
    assert "Uso administrativo" in html


def test_config_refresca_todo_despues_de_subir():
    js = _js()
    assert "await fetchPing()" in js
    assert "await fetchStats()" in js
    assert "performSearch()" in js
