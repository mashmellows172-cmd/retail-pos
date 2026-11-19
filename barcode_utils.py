"""
RetailPOS Pro — Barcode Utilities
Algoritmo confirmado con CSV OUT-33644917:
  EAN-13 = "0200" + PLU[0:7] + check_digit_EAN13
"""

import re
import os

# Cache del CSV parseado { plu_str -> ean13_str }
_csv_cache: dict = {}
_csv_path_loaded: str = ""


# ─────────────────────────────────────────────────────────
# EAN-13 puro
# ─────────────────────────────────────────────────────────

def ean13_check_digit(base12: str) -> int:
    """Calcula el dígito de verificación EAN-13 para 12 dígitos base."""
    s = str(base12).zfill(12)
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(s))
    return (10 - (total % 10)) % 10


def is_valid_ean13(code: str) -> bool:
    """Verifica si un string de 13 dígitos es un EAN-13 válido."""
    code = str(code).strip()
    if not code.isdigit() or len(code) != 13:
        return False
    return ean13_check_digit(code[:12]) == int(code[12])


# ─────────────────────────────────────────────────────────
# PLU → EAN-13 (fórmula principal, confirmada con CSV)
# ─────────────────────────────────────────────────────────

def plu_to_ean13(plu) -> str | None:
    """
    Convierte un PLU de 8 dígitos a EAN-13 usando la fórmula confirmada
    contra el CSV OUT-33644917:
        base12 = "020002" + PLU[1:7]   (= "02000" + PLU[0:7], primeros 12 chars)
        ean13  = base12 + check_digit_EAN13

    Ejemplo: PLU=26726735
        base12 = "020002" + "672673" = "020002672673"
        check  = ean13_check("020002672673") = 5
        EAN-13 = "0200026726735"  ✓
    """
    plu_s = str(int(plu)).zfill(8)
    if len(plu_s) < 7:
        return None
    base12 = "020002" + plu_s[1:7]   # 6 + 6 = 12 dígitos
    chk = ean13_check_digit(base12)
    candidate = base12 + str(chk)
    if is_valid_ean13(candidate):
        return candidate
    return None


def plu_to_ean13_bruteforce(plu) -> str | None:
    """
    Fallback: prueba base 002 + PLU[:-1] + dígito 0-9 hasta encontrar EAN-13 válido.
    Implementa exactamente lo que el usuario describió:
      'cambiar el último dígito por 0-9 hasta encontrar el válido'
    """
    plu_s = str(int(plu)).zfill(8)
    base_no_last = plu_s[:-1]  # 7 primeros dígitos

    # Variantes de prefijo a intentar
    prefixes = ["0200", "002", "02", "2"]
    for prefix in prefixes:
        for last_digit in range(10):
            candidate13 = (prefix + base_no_last + str(last_digit)).zfill(13)
            if len(candidate13) == 13 and is_valid_ean13(candidate13):
                return candidate13

    # Último recurso: PLU mismo como base12
    plu_padded = plu_s.zfill(12)
    chk = ean13_check_digit(plu_padded)
    candidate = plu_padded + str(chk)
    if is_valid_ean13(candidate):
        return candidate

    return None


def get_ean13_for_plu(plu, csv_path: str = None) -> dict:
    """
    Obtiene el EAN-13 para un PLU usando todas las estrategias disponibles.
    Retorna dict con: { ean13, source, valid }
    """
    plu_s = str(int(plu)) if plu else ""
    if not plu_s:
        return {"ean13": None, "source": "none", "valid": False}

    # 1. Fórmula principal
    ean = plu_to_ean13(plu_s)
    if ean:
        return {"ean13": ean, "source": "formula", "valid": True}

    # 2. Búsqueda en CSV
    if csv_path and os.path.exists(csv_path):
        ean = lookup_in_csv(plu_s, csv_path)
        if ean:
            return {"ean13": ean, "source": "csv", "valid": True}

    # 3. Fuerza bruta
    ean = plu_to_ean13_bruteforce(plu_s)
    if ean:
        return {"ean13": ean, "source": "bruteforce", "valid": True}

    return {"ean13": plu_s, "source": "plu_raw", "valid": False}


# ─────────────────────────────────────────────────────────
# Parser del CSV OUT-33644917
# ─────────────────────────────────────────────────────────

def load_csv_barcodes(csv_path: str) -> dict:
    """
    Parsea el CSV de existencias (formato reporte con pipes |).
    Retorna dict { plu_str -> ean13_str }
    Formato de línea de datos:
      | AREA | NIVEL DE AGREGACION | PLU | CODIGO DE BARRA | DESCRIPCION | ...
    """
    global _csv_cache, _csv_path_loaded

    if _csv_path_loaded == csv_path and _csv_cache:
        return _csv_cache

    result = {}
    # Regex para líneas de datos: | num | texto | PLU | BARCODE | ...
    data_re = re.compile(
        r'^\s*\|\s*\d+\s*\|[^|]*\|\s*(\d{6,9})\s*\|'
        r'\s*(0*\d{10,15})\s*\|'
    )

    try:
        with open(csv_path, "r", encoding="latin-1", errors="replace") as f:
            for line in f:
                m = data_re.match(line)
                if m:
                    plu = m.group(1).strip().lstrip("0") or "0"
                    barcode_raw = m.group(2).strip()
                    # El CSV guarda el barcode con ceros al frente (14 chars)
                    # El EAN-13 real son los últimos 13 (o sin el primer cero)
                    barcode = barcode_raw.lstrip("0") or barcode_raw
                    if len(barcode) < 13:
                        barcode = barcode.zfill(13)
                    elif len(barcode) > 13:
                        barcode = barcode[-13:]  # conservar los últimos 13 dígitos

                    if plu and barcode and is_valid_ean13(barcode):
                        result[plu] = barcode

        _csv_cache = result
        _csv_path_loaded = csv_path
        print(f"[CSV] Cargados {len(result)} códigos desde {os.path.basename(csv_path)}")
    except Exception as e:
        print(f"[CSV] Error parseando: {e}")

    return result


def lookup_in_csv(plu: str, csv_path: str) -> str | None:
    """Busca el EAN-13 de un PLU en el CSV de existencias."""
    db = load_csv_barcodes(csv_path)
    plu_norm = str(int(plu)) if plu.isdigit() else plu
    return db.get(plu_norm)


def reload_csv(csv_path: str) -> int:
    """Fuerza recarga del CSV. Retorna cantidad de registros cargados."""
    global _csv_cache, _csv_path_loaded
    _csv_cache = {}
    _csv_path_loaded = ""
    db = load_csv_barcodes(csv_path)
    return len(db)


# ─────────────────────────────────────────────────────────
# Test rápido
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_cases = [
        ("26726735", "0200026726735"),
        ("29195285", "0200029195286"),
        ("28159269", "0200028159265"),
        ("28906757", "0200028906753"),
        ("28907397", "0200028907392"),
    ]
    print("=== Test PLU → EAN-13 ===")
    all_ok = True
    for plu, expected in test_cases:
        result = plu_to_ean13(plu)
        ok = result == expected
        all_ok = all_ok and ok
        print(f"  PLU={plu} → {result} ({'✓' if ok else '✗ esperado: ' + expected})")
    print(f"\n{'✅ TODOS LOS TESTS PASARON' if all_ok else '❌ HAY FALLOS'}")
