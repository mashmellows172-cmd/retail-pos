"""Persistencia durable de los archivos semanales en Vercel Blob.

El filesystem de Vercel es efímero: cada instancia nueva arranca sin los
archivos subidos. Cuando el proyecto tiene conectado un Blob store, Vercel
inyecta ``BLOB_READ_WRITE_TOKEN`` y este módulo guarda una copia fuera de la
instancia para restaurarla en el siguiente arranque en frío.

Sin token el módulo queda inactivo y todo sigue funcionando con el
filesystem local (útil para desarrollo).
"""
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request

BASE_URL = "https://blob.vercel-storage.com"
PREFIX = "retailpos"


def token():
    return os.environ.get("BLOB_READ_WRITE_TOKEN", "").strip()


def access():
    return os.environ.get("BLOB_ACCESS", "private").strip() or "private"


def enabled():
    return bool(token())


def _request(url, method="GET", data=None, headers=None, timeout=30):
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", f"Bearer {token()}")
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def safe_name(filename):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", os.path.basename(filename or "archivo"))


def save(kind, filename, content):
    """Sube el archivo a Blob y retorna su pathname (o None si está inactivo)."""
    if not enabled():
        return None
    digest = hashlib.sha256(content).hexdigest()[:16]
    extension = os.path.splitext(filename)[1].lower() or ".bin"
    pathname = f"{PREFIX}/{kind}-{digest}-{safe_name(filename)}"
    if not pathname.endswith(extension):
        pathname += extension
    _request(
        f"{BASE_URL}/{urllib.parse.quote(pathname)}",
        method="PUT",
        data=content,
        headers={
            "x-api-version": "13",
            "x-vercel-blob-access": access(),
            "x-content-type": "application/octet-stream",
            "x-add-random-suffix": "0",
            "x-cache-control-max-age": "0",
        },
    )
    return pathname


def latest(kind):
    """Retorna el blob más reciente de un tipo ('excel' o 'csv')."""
    if not enabled():
        return None
    prefix = urllib.parse.quote(f"{PREFIX}/{kind}-")
    raw = _request(f"{BASE_URL}?prefix={prefix}&limit=20")
    payload = json.loads(raw or b"{}")
    blobs = payload.get("blobs") or []
    if not blobs:
        return None
    blobs.sort(key=lambda blob: blob.get("uploadedAt") or "", reverse=True)
    return blobs[0]


def name_from_pathname(pathname, fallback):
    """Extrae el nombre original desde 'retailpos/excel-<hash>-<nombre>'."""
    base = os.path.basename(pathname or "")
    parts = base.split("-", 2)
    if len(parts) == 3 and parts[2]:
        return parts[2]
    return fallback


def download(item, destination):
    url = item.get("url") or item.get("downloadUrl")
    if not url:
        return None
    data = _request(url)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    tmp = destination + ".download"
    with open(tmp, "wb") as handle:
        handle.write(data)
    os.replace(tmp, destination)
    return destination


def restore(kind, destination):
    """Descarga el último blob de un tipo hacia ``destination``."""
    if not enabled():
        return None
    try:
        item = latest(kind)
        if not item:
            return None
        download(item, destination)
        return item
    except Exception as exc:  # pragma: no cover - depende de la red
        print(f"[BLOB] No se pudo restaurar {kind}: {exc}")
        return None
