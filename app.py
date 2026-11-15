"""
RetailPOS Pro - Servidor Flask Principal v2
PWA + mobile-first + EAN-13 desde PLU + CSV fallback
"""
import os
import sys
import io
import base64
import threading
import webbrowser
from pathlib import Path
from flask import Flask, jsonify, request, render_template, send_from_directory, Response

import data_loader as dl
import barcode_utils as bu

# ──────────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["JSON_SORT_KEYS"] = False

_local_excel = os.path.join(os.path.dirname(__file__), "tiendas.xlsx")
_desktop_excel = r"C:\Users\victus\OneDrive\Desktop\MSM W45 (11.11 - 17.11) TIENDAS.xlsx"

EXCEL_PATH_DEFAULT = os.environ.get(
    "EXCEL_PATH",
    _local_excel if os.path.exists(_local_excel) else _desktop_excel
)
CSV_PATH_DEFAULT = os.environ.get(
    "CSV_PATH",
    r"C:\Users\victus\Downloads\OUT-33644917.csv"
)

_state = {
    "excel_path": EXCEL_PATH_DEFAULT if os.path.exists(EXCEL_PATH_DEFAULT) else None,
    "csv_path": CSV_PATH_DEFAULT if os.path.exists(CSV_PATH_DEFAULT) else None,
}

# Pre-cargar Excel al inicio
if _state["excel_path"]:
    dl.set_excel_path(_state["excel_path"])

# ──────────────────────────────────────────────
# App Shell / PWA
# ──────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/sw.js")
def service_worker():
    return send_from_directory("static", "sw.js",
                               mimetype="application/javascript")

@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json",
                               mimetype="application/manifest+json")

# ──────────────────────────────────────────────
# API: Excel
# ──────────────────────────────────────────────
@app.route("/api/set-excel", methods=["POST"])
def set_excel():
    data = request.get_json(force=True)
    path = data.get("path", "").strip()
    if not path or not os.path.exists(path):
        return jsonify({"ok": False, "error": "Archivo no encontrado"}), 400
    dl.set_excel_path(path)
    _state["excel_path"] = path
    return jsonify({"ok": True, "stats": dl.get_stats(path), "path": path})

@app.route("/api/upload-excel", methods=["POST"])
def upload_excel():
    """Recibe el Excel via multipart upload (para usar en móvil/Vercel)."""
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No se recibió archivo"}), 400
    f = request.files["file"]
    if not f.filename.endswith((".xlsx", ".xls")):
        return jsonify({"ok": False, "error": "Solo se aceptan archivos Excel"}), 400
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    path = os.path.join(upload_dir, "current.xlsx")
    f.save(path)
    dl.set_excel_path(path)
    _state["excel_path"] = path
    return jsonify({"ok": True, "stats": dl.get_stats(path), "filename": f.filename})

@app.route("/api/stats")
def stats():
    path = _state["excel_path"]
    if not path:
        return jsonify({})
    return jsonify(dl.get_stats(path))

@app.route("/api/brands")
def brands():
    operadora = request.args.get("operadora")
    path = _state["excel_path"]
    return jsonify(dl.get_brands(operadora, path) if path else [])

# ──────────────────────────────────────────────
# API: Búsqueda
# ──────────────────────────────────────────────
@app.route("/api/search")
def search():
    query     = request.args.get("q", "")
    operadora = request.args.get("op", "") or None
    marca     = request.args.get("marca", "") or None
    min_dcto  = request.args.get("min_dcto")
    max_precio= request.args.get("max_precio")
    path      = _state["excel_path"]
    if not path:
        return jsonify([])
    results = dl.search(
        query=query, operadora=operadora, marca=marca,
        min_dcto=int(min_dcto) if min_dcto else None,
        max_precio=int(max_precio) if max_precio else None,
        path=path,
    )
    # Enriquecer con EAN-13 calculado
    csv_path = _state["csv_path"]
    for r in results:
        plu = r.get("plu_cod", "")
        if plu and plu.isdigit():
            bc = bu.get_ean13_for_plu(plu, csv_path)
            r["ean13"] = bc["ean13"]
            r["ean13_source"] = bc["source"]
    return jsonify(results)

# ──────────────────────────────────────────────
# API: CSV de existencias
# ──────────────────────────────────────────────
@app.route("/api/csv-status")
def csv_status():
    path = _state["csv_path"]
    if path and os.path.exists(path):
        count = len(bu.load_csv_barcodes(path))
        return jsonify({"ok": True, "path": path, "records": count})
    return jsonify({"ok": False, "records": 0})

@app.route("/api/upload-csv", methods=["POST"])
def upload_csv():
    """Recibe el CSV de existencias vía upload."""
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No se recibió archivo"}), 400
    f = request.files["file"]
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    path = os.path.join(upload_dir, "existencias.csv")
    f.save(path)
    count = bu.reload_csv(path)
    _state["csv_path"] = path
    return jsonify({"ok": True, "records": count, "filename": f.filename})

@app.route("/api/reload-csv", methods=["POST"])
def reload_csv():
    path = _state["csv_path"]
    if not path or not os.path.exists(path):
        return jsonify({"ok": False, "error": "CSV no configurado"}), 400
    count = bu.reload_csv(path)
    return jsonify({"ok": True, "records": count})

# ──────────────────────────────────────────────
# API: Códigos de barras
# ──────────────────────────────────────────────
@app.route("/api/barcode-inline/<code>")
def barcode_inline(code):
    """Retorna SVG Code128 para cualquier código (COD_BARRA, PLAN, EAN-13)."""
    try:
        import barcode as bc
        from barcode.writer import SVGWriter
        clean = str(code).strip()
        if not clean:
            return Response("<svg/>", mimetype="image/svg+xml")
        buf = io.BytesIO()
        code128 = bc.get("code128", clean, writer=SVGWriter())
        code128.write(buf, options={
            "module_height": 14.0, "module_width": 0.28,
            "quiet_zone": 2.5, "font_size": 8,
            "text_distance": 2.5, "background": "white", "foreground": "black",
            "write_text": True,
        })
        return Response(buf.getvalue(), mimetype="image/svg+xml")
    except Exception as e:
        return Response(f"<svg><text y='20'>{e}</text></svg>", mimetype="image/svg+xml")

@app.route("/api/ean13/<plu>")
def get_ean13(plu):
    """Retorna el EAN-13 calculado para un PLU."""
    result = bu.get_ean13_for_plu(plu, _state["csv_path"])
    return jsonify(result)

# ──────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────
@app.route("/api/ping")
def ping():
    return jsonify({
        "ok": True,
        "excel": _state["excel_path"],
        "csv": _state["csv_path"],
        "version": "2.0"
    })

# ──────────────────────────────────────────────
# Arranque local
# ──────────────────────────────────────────────
def open_browser():
    import time; time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    t = threading.Thread(target=open_browser, daemon=True)
    t.start()
    print("=" * 50)
    print("  RetailPOS Pro v2 — http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
