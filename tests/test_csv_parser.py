"""El parser del reporte de existencias debe leer el formato real."""
import barcode_utils as bu


def test_parsea_linea_real_del_reporte(tmp_path):
    report = tmp_path / "existencias.csv"
    report.write_text(
        " |  1   |7880 PEQUENA                |26726735  |00200026726735 | DESC |\n",
        encoding="latin-1",
    )
    assert bu.reload_csv(str(report)) == 1
    assert bu.lookup_in_csv("26726735", str(report)) == "0200026726735"


def test_parsea_formato_compacto_y_evita_duplicados(tmp_path):
    report = tmp_path / "compacto.csv"
    line = "| 1 |X| 29195285| 00200029195286|\n"
    report.write_text(line + line, encoding="latin-1")
    assert bu.reload_csv(str(report)) == 1
    assert bu.lookup_in_csv("29195285", str(report)) == "0200029195286"


def test_ignora_lineas_sin_plu_o_sin_codigo(tmp_path):
    report = tmp_path / "mixto.csv"
    report.write_text(
        " |  1   |SIN PLU                    |          |               |\n"
        " |  2   |SIN BARCODE                |12345678  |               |\n",
        encoding="latin-1",
    )
    assert bu.reload_csv(str(report)) == 0
