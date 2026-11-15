"""
RetailPOS Pro - Data Loader
Carga y normaliza el Excel de planes de telefonía (CLARO / WOM / ENTEL)
"""
import pandas as pd
import os
import hashlib
import json
from datetime import datetime

EXCEL_PATH = None
_cache = {}

OPERADORAS = ["CLARO", "WOM", "ENTEL"]

OPERADORA_COLORS = {
    "CLARO": "#E8003D",
    "WOM": "#6B2D8B",
    "ENTEL": "#FF6B00",
}


def set_excel_path(path: str):
    global EXCEL_PATH, _cache
    EXCEL_PATH = path
    _cache = {}


def _file_hash(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return ""


def load_all(path: str = None) -> dict:
    """
    Carga las tres hojas del Excel y retorna un dict con DataFrames normalizados.
    Usa caché basado en hash del archivo.
    """
    target = path or EXCEL_PATH
    if not target or not os.path.exists(target):
        return {}

    file_hash = _file_hash(target)
    if _cache.get("hash") == file_hash and _cache.get("data"):
        return _cache["data"]

    result = {}
    for sheet in OPERADORAS:
        try:
            df = pd.read_excel(target, sheet_name=sheet)
            df = _normalize(df, sheet)
            result[sheet] = df
        except Exception as e:
            print(f"[WARN] No se pudo cargar hoja {sheet}: {e}")

    _cache["hash"] = file_hash
    _cache["data"] = result
    _cache["loaded_at"] = datetime.now().isoformat()
    return result


def _normalize(df: pd.DataFrame, operadora: str) -> pd.DataFrame:
    """Normaliza columnas y tipos para una hoja dada."""
    df = df.copy()

    # Renombrar columnas de forma estándar
    rename_map = {}
    for col in df.columns:
        col_up = str(col).upper().strip()
        if "MARCA" in col_up:
            rename_map[col] = "marca"
        elif "PLU" in col_up:
            rename_map[col] = "plu_cod"
        elif "DESCRIPCI" in col_up:
            rename_map[col] = "descripcion"
        elif "COD" in col_up and "BARRA" in col_up:
            rename_map[col] = "cod_barra"
        elif "PLAN" in col_up:
            rename_map[col] = "plan"
        elif "DCTO" in col_up:
            rename_map[col] = "descuento"
        elif col_up in ("CLARO", "WOM", "ENTEL"):
            rename_map[col] = "precio"
        elif "DESDE" in col_up:
            rename_map[col] = "desde"
        elif "HASTA" in col_up:
            rename_map[col] = "hasta"

    df = df.rename(columns=rename_map)

    # Asegurar columnas requeridas
    for col in ["marca", "plu_cod", "descripcion", "cod_barra", "plan", "descuento", "precio"]:
        if col not in df.columns:
            df[col] = None

    # Limpiar nulos en columnas clave
    df = df.dropna(subset=["plu_cod"])

    # Tipos
    df["plu_cod"] = pd.to_numeric(df["plu_cod"], errors="coerce").astype("Int64")
    df["cod_barra"] = pd.to_numeric(df["cod_barra"], errors="coerce").astype("Int64")
    df["plan"] = pd.to_numeric(df["plan"], errors="coerce").astype("Int64")
    df["descuento"] = pd.to_numeric(df["descuento"], errors="coerce").fillna(0).astype(int)
    df["precio"] = pd.to_numeric(df["precio"], errors="coerce").fillna(0).astype(int)

    # Texto
    df["marca"] = df["marca"].astype(str).str.upper().str.strip()
    df["descripcion"] = df["descripcion"].astype(str).str.strip()

    # Fecha vigencia
    for col in ["desde", "hasta"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    df["operadora"] = operadora
    df["precio_final"] = (df["precio"] - df["descuento"]).clip(lower=0)

    # Columna de búsqueda combinada
    df["_busqueda"] = (
        df["marca"].fillna("") + " " +
        df["descripcion"].fillna("") + " " +
        df["plu_cod"].astype(str).fillna("") + " " +
        df["cod_barra"].astype(str).fillna("")
    ).str.upper()

    return df.reset_index(drop=True)


def search(query: str, operadora: str = None, marca: str = None,
           min_dcto: int = None, max_precio: int = None,
           path: str = None) -> list:
    """
    Busca productos en el Excel cargado.
    Retorna lista de dicts listos para JSON.
    """
    all_data = load_all(path)
    frames = []

    operadoras_target = [operadora.upper()] if operadora and operadora.upper() in all_data else list(all_data.keys())

    for op in operadoras_target:
        if op not in all_data:
            continue
        df = all_data[op].copy()

        # Filtro por marca
        if marca and marca.upper() != "TODAS":
            df = df[df["marca"] == marca.upper()]

        # Filtro por descuento mínimo
        if min_dcto:
            df = df[df["descuento"] >= int(min_dcto)]

        # Filtro por precio máximo
        if max_precio:
            df = df[df["precio"] <= int(max_precio)]

        # Filtro por texto / código de barras
        if query and query.strip():
            q = query.upper().strip()
            mask = df["_busqueda"].str.contains(q, na=False)
            # También intentar match exacto de código de barras
            if q.isdigit():
                mask = mask | (df["cod_barra"].astype(str) == q) | (df["plu_cod"].astype(str) == q)
            df = df[mask]

        frames.append(df)

    if not frames:
        return []

    combined = pd.concat(frames, ignore_index=True)
    return _to_records(combined)


def get_brands(operadora: str = None, path: str = None) -> list:
    """Retorna lista de marcas únicas para la operadora dada."""
    all_data = load_all(path)
    brands = set()
    targets = [operadora.upper()] if operadora else list(all_data.keys())
    for op in targets:
        if op in all_data:
            brands.update(all_data[op]["marca"].dropna().unique().tolist())
    return sorted(brands)


def get_stats(path: str = None) -> dict:
    """Retorna estadísticas rápidas del Excel cargado."""
    all_data = load_all(path)
    stats = {}
    for op, df in all_data.items():
        stats[op] = {
            "total": len(df),
            "marcas": int(df["marca"].nunique()),
            "dcto_max": int(df["descuento"].max()) if len(df) > 0 else 0,
            "dcto_min": int(df["descuento"].min()) if len(df) > 0 else 0,
            "precio_min": int(df["precio_final"].min()) if len(df) > 0 else 0,
            "precio_max": int(df["precio_final"].max()) if len(df) > 0 else 0,
        }
    return stats


def _to_records(df: pd.DataFrame) -> list:
    """Convierte DataFrame a lista de dicts serializables."""
    records = []
    for _, row in df.iterrows():
        records.append({
            "operadora": str(row.get("operadora", "")),
            "marca": str(row.get("marca", "")),
            "plu_cod": _safe_int(row.get("plu_cod")),
            "descripcion": str(row.get("descripcion", "")),
            "cod_barra": _safe_int(row.get("cod_barra")),
            "plan": _safe_int(row.get("plan")),
            "descuento": int(row.get("descuento", 0)),
            "precio": int(row.get("precio", 0)),
            "precio_final": int(row.get("precio_final", 0)),
            "desde": str(row["desde"].date()) if pd.notnull(row.get("desde")) else "",
            "hasta": str(row["hasta"].date()) if pd.notnull(row.get("hasta")) else "",
        })
    return records


def _safe_int(val) -> str:
    """Convierte a string evitando NaN/None."""
    try:
        if pd.isna(val):
            return ""
        return str(int(val))
    except Exception:
        return str(val) if val else ""
