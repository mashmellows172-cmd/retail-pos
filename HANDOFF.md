# Resumen de Entrega y Estado del Proyecto: RetailPOS Pro

**Repositorio en GitHub:** [https://github.com/mashmellows172-cmd/retail-pos](https://github.com/mashmellows172-cmd/retail-pos)  
**Despliegue en Producción (Vercel):** [https://retail-pos-pink.vercel.app/](https://retail-pos-pink.vercel.app/)  
**Directorio Local:** `C:\Users\victus\.gemini\antigravity\scratch\retail-pos\`

---

## 1. Arquitectura y Componentes Clave

1. **`app.py`**:
   - Backend Flask preparado para Serverless en Vercel y ejecución local (puerto 5050).
   - Manejo seguro de subida de archivos Excel y CSV a `/tmp/` para evitar bloqueos de solo lectura en funciones Lambda.
   - Endpoints REST para `/api/search`, `/api/stats`, `/api/brands`, `/api/barcode-inline/<code>`, `/api/upload-excel` y `/api/upload-csv`.

2. **`barcode_utils.py`**:
   - Algoritmo de cálculo de **código de barras EAN-13** probado y confirmado con el reporte real de existencias (`OUT-33644917.csv`):
     $$\text{base12} = \text{"020002"} + \text{PLU}[1:7]$$
     $$\text{EAN-13} = \text{base12} + \text{check\_digit\_EAN13}$$
   - Soporte de fallback contra el CSV maestro de existencias y fuerza bruta inteligente (0-9).

3. **`data_loader.py`**:
   - Parser multi-hoja de Excel para **CLARO**, **WOM** y **ENTEL**.
   - Normalización de datos, cálculo de precio final con descuento protegido contra negativos y optimización de búsqueda textual/numérica.
   - Mapeo de columnas del Excel: **D (`COD BARRA`)** → `plan_barcode`, el código que se pistolea para el descuento del plan de portabilidad; **E (`PLAN`)** → `plan`, solo código interno (no es un código de barras).

4. **Frontend PWA estilo iOS (`templates/index.html`, `static/app.css`, `static/app.js`, `static/sw.js`)**:
   - Shell semántico propio, sin Tailwind CDN ni Google Fonts: sistema visual iOS (canvas `#F2F2F7`, grupos blancos, segmented control, tab bar, safe-area).
   - Búsqueda directa con debounce, segmented por operadora, filtros en bottom sheet (móvil) o inline (escritorio), paginación de 40/50 y tabla + panel de detalle en desktop.
   - Detalle con orden **Equipo → Plan**, barcodes SVG sin texto embebido (`?text=0&quiet_zone=4`), copiado al portapapeles y voucher imprimible.
   - Stats por operadora y Configuración con carga de Excel/CSV, diagnóstico de caché e instalación PWA.
   - Offline: shell precacheado + última búsqueda exitosa en `localStorage['retailpos:lastSearch:v1']`.

5. **`vercel.json` y `requirements.txt`**:
   - Configuración Serverless Python para despliegues continuos tras cada `git push`.

---

## 2. Historial de Commits en `main`

- `0a1332c` — `fix(vercel): use /tmp directory for uploads in serverless environment`
- `d606d0a` — `docs: add comprehensive project README`
- `830e371` — `chore: update launch.bat to target port 5050`
- `548eb0d` — `fix(excel): fallback to local copy to prevent Windows file-lock issues`
- `6a4786d` — `feat(ui): complete mobile-first PWA dashboard with bottom sheet and EAN-13 barcodes`
- `a67a432` — `feat: RetailPOS Pro PWA con soporte EAN-13, barcode dinámico y Vercel ready`

---

## 3. Estado Actual

- El árbol de trabajo local y remoto está **sincronizado en `main`**.
- Los endpoints y la carga de archivos en Vercel están totalmente probados y respondiendo `200 OK`.
- **Persistencia del Excel:** Vercel usa un filesystem efímero. La app guarda el Excel elegido en el navegador (`localStorage['retailpos:seedExcel:v1']`) y lo vuelve a subir automáticamente cuando una instancia nueva arranca sin datos. Para persistencia real entre dispositivos, conecta un **Blob store** en Vercel (Storage → Blob): al desplegar, Vercel inyecta `BLOB_READ_WRITE_TOKEN` y `storage.py` guarda/restaura los archivos. Configuración muestra el estado en “Persistencia” (`Blob (permanente)` o `Local (se reinicia)`).
- Tras conectar Blob hay que subir el Excel una vez desde Configuración para dejarlo respaldado. Sin Blob, basta con subirlo una vez por dispositivo.
- Cualquier otro agente puede clonar directamente o continuar editando desde el repositorio `mashmellows172-cmd/retail-pos`.

---

## 4. Corrección reciente — código de barras del plan de portabilidad

**Problema:** el código de barras del plan se generaba desde la columna **E (`PLAN`)**, un código interno de 8 dígitos que no corresponde al código que se pistolea en caja. Eso producía errores al aplicar el descuento de portabilidad.

**Solución:** la API ahora expone `plan_barcode` tomado de la columna **D (`COD BARRA`)** y la UI (bottom sheet, panel de escritorio y ticket impreso) usa ese campo. La columna **E (`PLAN`)** se conserva solo como dato informativo.

**Regresión cubierta:** `tests/test_plan_barcode.py` valida el mapeo D/E en las tres hojas y que la UI no vuelva a usar `prod.plan` como código de barras. Ejecutar con `python -m pytest -q`.

**PWA:** el caché actual es **`retailpos-v3`** (barcodes en `retailpos-barcodes-v3`). Las navegaciones, la API, `app.css`, `app.js` y el manifest usan network-first; el resto de los assets, cache-first. Así un cambio de código se ve aunque no se suba el nombre del caché.

---

## 5. Rediseño de mostrador (iOS) — noviembre 2026

- **Diseño aprobado:** `docs/superpowers/specs/2026-11-16-rediseno-mostrador-design.md`; mockup en `docs/superpowers/specs/mockups/retailpos-mostrador.html`.
- **Plan de ejecución:** `docs/superpowers/plans/2026-11-16-rediseno-mostrador-ios.md`; ledger en `.superpowers/sdd/2026-11-16-rediseno-mostrador-ios/progress.md`.
- **Endpoints aditivos:** `/api/stats` devuelve `_rango` (`desde`, `hasta`, `semana`), `/api/ping` devuelve `excel_name`/`csv_name`, `/api/barcode-inline` acepta `?text=0&quiet_zone=4`.
- **Semana derivada:** `data_loader.business_week()` usa `ceil(día_del_año / 7)` para calzar con el rótulo W45 del archivo (11–17 nov = semana 45).
- **Iconos:** generar con `python tools/make_icons.py` (Pillow) si cambia la marca.
- **Pruebas:** `python -m pytest -q` (32 tests). Cobertura de contratos API, shell, búsqueda, detalle/impresión, stats/config, PWA e iconos.
- **Verificación manual:** Lighthouse 100/100/100 (accesibilidad, buenas prácticas, SEO), sin overflow horizontal de 360 a 1440 px, controles ≥ 44 px, offline restaura la última búsqueda.
