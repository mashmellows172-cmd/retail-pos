# RetailPOS Pro — Rediseño “Mostrador”

Fecha: 2026-11-16
Estado: propuesta para aprobación
Enfoque elegido: C — Rediseño de mostrador

## 1. Resumen

RetailPOS Pro es una PWA interna que usa un vendedor de tienda para encontrar un equipo por código o nombre y mostrar los códigos de barra que necesita escanear en caja. Hoy funciona, pero la interfaz está optimizada como panel de datos: muestra los 712 productos de entrada, usa un tema oscuro con textos de 10–11 px, targets táctiles pequeños y un detalle donde el código de plan queda en segundo plano.

Este rediseño convierte la app en una herramienta de mostrador: fondo claro y alto contraste para luz de tienda, una búsqueda protagonista, resultados paginados y un “modo escaneo” donde los dos códigos esenciales se ven en el orden real de uso: **primero Equipo, después Plan**. Se conserva la identidad de operadoras, el flujo offline, la impresión y todos los contratos actuales con Flask.

## 2. Intención y por qué

### Usuario principal

Vendedor o cajero de tienda, de pie, con teléfono o tablet, bajo luz artificial intensa y con un escáner de mano. Su tarea no es “explorar el catálogo”: es resolver una venta en menos de un minuto.

### Trabajo principal

1. Escanear o buscar el equipo.
2. Confirmar que el descuento y el precio final corresponden.
3. Mostrar o copiar el código del equipo.
4. Mostrar o copiar el código del plan de la operadora.
5. Imprimir el voucher si hace falta.

### Por qué ahora

- El arreglo de la columna D ya dejó el código de plan correcto (`plan_barcode`), pero la UI todavía lo presenta como un código secundario.
- La app se usa en producción desde Vercel y en tienda; el tema oscuro, el tamaño de texto y el volumen de DOM no están pensados para ese contexto.
- La auditoría con datos reales encontró 21.795 nodos, 110.202 px de scroll, 202 nodos con contraste insuficiente y 1.429 elementos clickeables que no se pueden operar con teclado.

### Éxito

Un vendedor puede escanear el equipo, ver ambos códigos completos sin buscar entre pestañas ni hacer scroll en un teléfono estándar, y volver a la búsqueda en pocos segundos. La app se siente rápida, legible y confiable incluso con poca batería, mala señal o luz fuerte.

## 3. Objetivos

### Objetivos de producto

1. Hacer evidente el orden **Equipo → Plan** dentro del detalle.
2. Mostrar ambos códigos completos y legibles en el mismo viewport de un teléfono de 390×844 px, sin scroll.
3. Reducir el tiempo entre “encuentro el producto” y “tengo el código listo para escanear”.
4. Eliminar la pared de 712 productos como primera impresión.
5. Distinguir claramente “no hay datos cargados” de “no hay resultados para esta búsqueda”.
6. Mantener la impresión del voucher y el uso offline.

### Objetivos técnicos

1. Reducir el DOM inicial a menos de 2.500 nodos con 40 resultados visibles.
2. Renderizar solo la vista activa (móvil o escritorio), no ambas.
3. Cumplir WCAG 2.1 AA en contraste, foco, teclado, zoom y tamaño de objetivos.
4. Servir el CSS compilado localmente, sin Tailwind CDN en producción.
5. Subir la versión del service worker para que el rediseño llegue a las PWA instaladas.
6. Mantener los tests existentes y agregar regresiones para el shell nuevo.

## 4. No objetivos

- No cambiar el modelo de datos, la lectura de Excel ni la regla `D = COD BARRA → plan_barcode`.
- No cambiar la codificación de códigos de barra ni el formato del voucher.
- No agregar login, roles ni permisos.
- No agregar una base de datos ni persistencia de archivos en Vercel.
- No reemplazar Flask por otro framework.
- No agregar modo oscuro conmutable; el tema de mostrador es claro por defecto.
- No rediseñar la app nativa ni crear una versión de escritorio separada.
- No implementar analítica, telemetría ni integración con el POS.

## 5. Anti-objetivos

El rediseño falla si:

- Vuelve a mostrar todo el catálogo como pantalla inicial.
- Esconde el código de plan detrás de un acordeón, pestaña o scroll.
- Usa iconos de copiar de 24 px o acciones que solo aparecen con hover.
- Depende del color para distinguir operadoras o estados.
- Rompe la impresión o el modo offline.
- Convierte el detalle en un panel de métricas y deja los códigos al final.
- Reemplaza la identidad de las operadoras por una paleta genérica.

## 6. Restricciones

- **Stack:** Flask + una plantilla Jinja (`templates/index.html`) con CSS y JavaScript inline. No hay bundler ni framework de frontend.
- **Hosting:** Vercel sirve la app Flask; el almacenamiento de archivos es efímero. La UI no puede asumir que el Excel sigue cargado tras un reinicio.
- **Datos:** 712 productos actuales; CLARO 285, WOM 227, ENTEL 200. Cada producto tiene `operadora`, `marca`, `descripcion`, `plu_cod`, `ean13`, `ean13_source`, `plan`, `plan_barcode`, `descuento`, `precio`, `precio_final`, `desde`, `hasta`.
- **Códigos:** el código de equipo puede venir del CSV o de la fórmula; el código de plan viene de `plan_barcode` (columna D). El PLU es interno y no es uno de los dos códigos principales de escaneo.
- **Barcodes:** se generan como SVG en `/api/barcode-inline/<code>`. Se pueden pedir sin texto embebido para la pantalla.
- **PWA:** existe `static/sw.js` con cache `retailpos-v2`; hay que subir a `v3` y precachear el CSS nuevo.
- **Impresión:** el voucher usa `@media print` y el contenedor `#printTicketContainer`.
- **Idioma:** español de Chile. Montos en CLP con separador de miles.
- **Dispositivos:** teléfono 360–430 px, tablet 768 px, escritorio 1024–1440 px.
- **Accesibilidad:** WCAG 2.1 AA como mínimo.
- **Sin dependencias de runtime nuevas:** el CSS se compila en desarrollo y se commitea; Vercel no ejecuta Node.
- **Cambios aditivos de backend permitidos:** se pueden agregar parámetros a `/api/barcode-inline` (`text`, `quiet_zone`), campos de metadatos a `/api/stats` y `/api/ping`, y guardar el nombre original del archivo en memoria. No se cambia el contrato existente ni la lectura de Excel.
- **Tipografía del sistema:** la UI usa la pila nativa (`-apple-system`, `SF Pro`, `Segoe UI`, `Roboto`) y los códigos usan `ui-monospace` (`SF Mono`, `Menlo`). Sin fuentes externas, sin WOFF2 y sin dependencia de Google Fonts.

## 7. Enfoques considerados

### A. Caja rápida

Rediseñar solo el flujo buscar → escanear, manteniendo el tema oscuro y el resto de la estructura. Mejora la jerarquía de códigos y corrige targets, pero deja el problema de legibilidad bajo luz de tienda y no renueva Stats/Config.

- Ventaja: menor riesgo visual.
- Desventaja: no resuelve la causa del cansancio visual ni la experiencia completa.

### B. Pulido seguro

No cambiar la estructura: paginación, accesibilidad, contraste, targets y CSS estático. La app se ve casi igual. Es el menor riesgo y el menor esfuerzo, pero mantiene la pared de productos y la jerarquía actual de códigos.

- Ventaja: rápido y conservador.
- Desventaja: no cumple el objetivo de “modo escaneo” ni el rediseño de mostrador.

### C. Rediseño de mostrador — elegido

Incluye lo mejor de A y B, más un sistema visual claro de alto contraste, nueva jerarquía, navegación simplificada, modo escaneo a pantalla completa y rediseño de Stats/Config.

- Ventaja: ataca la causa real (contexto de tienda y flujo de escaneo).
- Desventaja: es el cambio más grande; requiere reescribir la plantilla y validar con un escáner físico.
- Riesgo: medio-alto, mitigado con pruebas de aceptación y una implementación por fases.

**Decisión del usuario:** enfoque C. **Orden de escaneo confirmado:** Equipo y luego Plan.

## 8. Principios de diseño

1. **El código es el protagonista.** El descuento y los metadatos acompañan; no compiten con los códigos.
2. **Un paso se ve como un paso.** Los códigos llevan “1” y “2” para que el orden sea obvio.
3. **Todo se puede tocar.** Ningún control esencial mide menos de 44×44 px.
4. **Claro no significa plano.** El alto contraste y la jerarquía tipográfica reemplazan sombras y gradientes.
5. **La app responde antes de decorar.** Primero los resultados útiles, después el detalle.
6. **Nada importante depende del color.** Las operadoras tienen color, pero también texto y forma.
7. **Offline es un estado normal.** La app debe verse completa sin conexión y decir qué está pasando.

## 9. Sistema visual “Mostrador claro · iOS”

El estilo es iOS nativo: listas agrupadas, tipografía del sistema, controles de 44 px, materiales translúcidos y jerarquía por peso tipográfico. Se conserva el alto contraste para luz de tienda.

### Paleta

| Token | Valor | Uso |
|---|---|---|
| `canvas` | `#F2F2F7` | Fondo agrupado |
| `surface` | `#FFFFFF` | Tarjetas, listas y panel |
| `surface-muted` | `rgba(118,118,128,0.12)` | Campos, segmentos y botones secundarios |
| `ink` | `#1C1C1E` | Texto principal |
| `ink-secondary` | `#3A3A3C` | Texto secundario |
| `muted` | `#6C6C70` | Metadatos; 5.23:1 sobre blanco y 4.69:1 sobre `canvas` |
| `separator` | `rgba(60,60,67,0.29)` | Hairline de 0.5–1 px |
| `tint` | `#0066CC` | Acciones y foco; 5.57:1 sobre blanco |
| `success` | `#1E7A34` | Descuento y precio final; 5.40:1 sobre blanco |
| `danger` | `#D70015` | Errores; 5.38:1 sobre blanco |
| `warning-bg` | `#FFF8E5` | Banner offline |
| `warning-ink` | `#6B4E00` | Texto del banner offline |

`#007AFF` (systemBlue de iOS) se usa solo en elementos decorativos y nunca como texto pequeño ni como fondo con texto blanco: blanco sobre `#007AFF` da 4.02:1. Toda acción interactiva usa `#0066CC`. Los verdes y rojos brillantes de iOS (`#34C759`, `#FF3B30`) se reservan para puntos decorativos; el texto usa las variantes accesibles.

### Colores de operadora

Se mantiene el reconocimiento de marca, pero con pares accesibles:

| Operadora | Color de marca | Texto sobre color | Contraste |
|---|---|---|---|
| CLARO | `#C8102E` | `#FFFFFF` | 5.88:1 |
| WOM | `#6B2D8B` | `#FFFFFF` | 8.85:1 |
| ENTEL | `#C2410C` | `#FFFFFF` | 5.18:1 |
| TODAS | `#0066CC` | `#FFFFFF` | 5.57:1 |

El naranja brillante `#FF6B00` se puede usar como punto o acento decorativo, nunca como fondo de texto blanco.

### Tipografía

- **UI:** `-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`.
- **Códigos:** `ui-monospace, "SF Mono", Menlo, Consolas, monospace`, con `font-variant-numeric: tabular-nums`.
- **Escala iOS:** 34 / 28 / 22 / 17 / 15 / 13 / 11 px.
- **Cuerpo:** 17 px, line-height 1.35; secundario 15 px; caption 13 px; etiquetas de tab 10 px.
- **Títulos:** large title 34 px/700 en Stats y Config; cabecera de vista 22 px/700; fila 17 px/600; botón 17 px/600.
- **Número de código:** 22 px mono, tracking `0.08em`.
- **Sin fuentes web:** la tipografía del sistema no se descarga ni se precachea.

### Formas y materiales

- Radios: 10 px para listas agrupadas y campos, 12 px para botones, 999 px solo para indicadores y avatares.
- **Barras translúcidas:** `background: rgba(255,255,255,0.82); backdrop-filter: saturate(180%) blur(20px)` con hairline inferior.
- Separadores hairline que no llegan al borde izquierdo del texto.
- Sombra solo en el segmento activo y en el sheet: `0 0 0 0.5px rgba(0,0,0,0.04), 0 3px 8px rgba(0,0,0,0.12)`.
- Sin gradientes. Los grupos de listas viven sobre `canvas`; cada grupo es blanco.
- **Indicador de inicio:** barra de 134×5 px, `rgba(0,0,0,0.85)`, centrada sobre el área segura inferior en el mockup y en pantalla completa móvil.

### Iconografía

- Estilo SF Symbols: trazo redondeado de 1.8–2 px, 25 px en la tab bar y 20 px en filas.
- Sin emojis como iconos.
- Iconos decorativos con `aria-hidden="true"`.
- Botones icono-solo con `aria-label`.

## 10. Arquitectura de información

### Navegación

- **Móvil:** tab bar inferior translúcida de 49 px + `env(safe-area-inset-bottom)`, con 3 destinos: **Buscar**, **Stats**, **Config**. Iconos SF Symbols de 25 px y etiqueta de 10 px; el activo usa `tint`. Sin menú hamburguesa.
- **Escritorio:** navegación en el header con los mismos 3 destinos, estilo segmented; la tab bar inferior se oculta.
- Se elimina el drawer hamburguesa y sus atajos duplicados.

### Header

- Barra compacta translúcida de 44 px en móvil y 64 px en escritorio, con hairline inferior.
- Izquierda: marca “RetailPOS” + subtítulo de semana (“Semana 45 · 11–17 nov”).
- Derecha: estado de conexión (“En línea” / “Sin conexión”) con punto + texto, no solo color.
- Stats y Config usan large title de 34 px dentro del contenido, no en la barra.
- En Buscar, el campo de búsqueda ocupa el lugar del título.
- Sin badge “PWA” en la cabecera; ese término queda solo en Configuración > Avanzado.

### Vistas

1. **Buscar** (principal).
2. **Stats** (supervisor).
3. **Config** (administración).
4. **Detalle / Modo escaneo** (capa a pantalla completa en móvil, panel en escritorio).
5. **Filtros** (bottom sheet en móvil, barra inline en escritorio).
6. **Voucher de impresión** (solo `@media print`).

## 11. Pantallas y componentes

### 11.1 Buscar — estado inicial

La app no llama a `/api/search` al cargar si no hay texto, operadora ni filtros. En su lugar muestra:

- Título: “Escanea o busca un equipo”.
- Campo de búsqueda grande estilo iOS: relleno `surface-muted`, radio 10 px, altura 44 px, icono de lupa y placeholder “Escanea el código o busca…”.
- Tres pasos visuales dentro de una lista agrupada:
  1. “Escanea el código del equipo”.
  2. “Revisa el descuento”.
  3. “Muestra el código del plan”.
- Botón secundario “Ver todo el catálogo” como botón de texto `tint` de 48 px o botón relleno `surface-muted` según el diseño final.
- Si `/api/ping` indica que no hay Excel: estado “No hay precios cargados” con botón “Ir a Configuración”.
- Si hay CSV pero no Excel, el estado sigue siendo “No hay precios cargados”; el CSV solo afecta el EAN.

### 11.1.1 Selector de operadora

- Se usa un **segmented control** iOS de 4 segmentos debajo de la búsqueda: **Todas**, **Claro**, **WOM**, **Entel**, con conteo en caption de 11 px.
- Altura 44 px; pista `surface-muted` con radio 10 px; segmento activo blanco con sombra suave y texto `ink`; inactivo `ink-secondary`.
- Sin scroll horizontal: los 4 segmentos caben desde 360 px.
- Implementación semántica: `role="tablist"` + `role="tab"` + `aria-selected`, o `role="radiogroup"` + `role="radio"`; nunca `aria-pressed` sobre divs.
- La operadora sigue siendo un filtro primario, no se esconde dentro del sheet de filtros.
- Al cargar la app se lee `?op=CLARO|WOM|ENTEL` de la URL y se aplica el segmento correspondiente, para que los atajos del manifest sigan funcionando.
- Cambiar de operadora resetea la paginación y vuelve a consultar.

### 11.2 Buscar — resultados móvil

- Lista agrupada estilo iOS: un bloque blanco con radio 10 px sobre `canvas`, separadores hairline y sin sombra por fila.
- Cada fila es un `<button>` de ancho completo, altura mínima 76 px.
- Contenido:
  - Píldora de operadora (color accesible + texto) + marca en caption.
  - Descripción en 2 líneas máximo, 17 px/600.
  - PLU en 13 px `muted`.
  - Descuento en `success` y precio final en `ink`, alineados a la derecha, con cifras tabulares.
  - Chevron SF Symbols `chevron.right` en `muted`.
- Contador de resultados en 13 px `muted` con `aria-live="polite"`.
- 40 resultados por página.
- “Cargar más” como botón de texto `tint` de 48 px al final; desaparece cuando no hay más.

### 11.3 Buscar — resultados escritorio

- Layout de 12 columnas: 7 para tabla, 5 para detalle sticky.
- Tabla dentro de un grupo blanco con radio 10 px y header caption de 11 px en mayúsculas.
- Columnas: Operadora, Producto (marca + descripción), PLU, Dcto, Precio final, Acción.
- Se eliminan EAN-13 y Plan de la tabla; viven en el detalle para reducir ruido y scroll horizontal.
- Fila seleccionada con fondo `rgba(0,102,204,0.10)` y texto `ink`, no solo un ring.
- La acción “Ver códigos” es un `<button>` de texto `tint` de 44 px. El click en la fila sigue funcionando como atajo, pero no es la única vía.
- El detalle se auto-selecciona con el primer resultado solo si no hay selección previa.
- 50 resultados por página.

### 11.4 Filtros

- **Móvil:** bottom sheet estilo iOS con grabber de 36×5 px, esquinas superiores de 12 px, backdrop oscuro y safe area:
  - Marca (select de 44 px).
  - Descuento mínimo (input numérico de 44 px).
  - Precio máximo (input numérico de 44 px).
  - “Aplicar filtros” (50 px, relleno `tint`).
  - “Limpiar” (44 px, botón de texto `tint`).
  - Cerrar con X de 44 px, Escape y backdrop.
- **Escritorio:** barra inline bajo la búsqueda con los mismos controles.
- Indicador de filtros activos: texto “2 filtros activos” + botón “Limpiar”, no solo un punto.

### 11.5 Detalle / Modo escaneo — móvil

Se abre como una vista a pantalla completa, no como un bottom sheet de 90vh.

Estructura:

1. **Nav bar translúcida (44 px):** chevron `tint` para volver, título 17 px/600 y operadora como subtítulo de 11 px.
2. **Resumen compacto** en lista agrupada: descuento 28 px en `success` y precio final 22 px; “Copiar descuento” como botón de texto `tint` de 44 px.
3. **Section header:** “CÓDIGOS PARA ESCANEAR” en 13 px `muted`, con separador hairline.
4. **Paso 1 — Código del equipo:**
   - Chip “1” de 22 px relleno `tint`.
   - Etiqueta “Código del equipo” 15 px/600.
   - Área blanca con barcode SVG, quiet zone visible, sin texto embebido.
   - Fila inferior: número en mono 22 px a la izquierda y botón de texto “Copiar” de 44 px a la derecha. La fila evita apilar un botón extra y mantiene la tarjeta compacta.
5. **Paso 2 — Código del plan:**
   - Chip “2”.
   - Etiqueta “Código del plan · CLARO/WOM/ENTEL”.
   - Mismo tratamiento.
6. **Detalles** (`<details>`): fila estilo iOS con chevron; PLU, origen del EAN (“CSV” o “Calculado”), vigencia, precio normal.
7. **Footer fijo (64 px + safe area):** “Imprimir códigos” relleno `tint` de 50 px, radio 12, e indicador de inicio.

Reglas:

- Los dos códigos van apilados a ancho completo. No se ponen en dos columnas en teléfono: el barcode quedaría demasiado angosto para escanear.
- Cada tarjeta de código ocupa ~190 px; nav + resumen + dos tarjetas + footer deben caber en 390×844 sin scroll. En 360×640 ambos códigos deben quedar visibles con scroll mínimo.
- El botón de copiar no cubre el barcode; se evita el copiado accidental al intentar escanear.
- El número también se puede tocar para copiar, con `aria-label`.
- No hay tabs, acordeones ni carrusel para los dos códigos principales.

### 11.6 Detalle / Modo escaneo — escritorio

- Panel sticky de 5 columnas, `top: 88px`, con scroll interno si hace falta.
- Mismo orden Equipo → Plan.
- Dos tarjetas agrupadas apiladas; ancho completo del panel.
- Header del panel con producto, operadora y botón cerrar de 44 px.
- Footer del panel con “Imprimir códigos” relleno `tint`.
- Si no hay selección: estado vacío “Selecciona un producto para ver sus códigos”.

### 11.7 Stats

- Large title “Estadísticas” de 34 px/700 + subtítulo 15 px `muted`.
- Tres grupos blancos, uno por operadora, con círculo de 28 px en el color accesible y nombre 17 px/600.
- KPI principal: total de equipos en 34 px/700.
- Secundarios en 13 px: marcas, máximo descuento, rango de precios.
- Acción “Ver productos” como botón de texto `tint` de 44 px; la tarjeta no es clickeable.
- Estado de carga con skeletons de 3 grupos.
- Estado de error con reintento.

### 11.8 Config

- Large title “Configuración” de 34 px/700 + subtítulo 15 px `muted`.
- Listas agrupadas estilo Ajustes de iOS:
  - **Datos:** Excel de precios (primario) y CSV de existencias (secundario).
  - Cada fila con icono cuadrado redondeado de 29 px, título 17 px, descripción 13 px, botón de 50 px y estado con nombre de archivo o “Sin archivo”.
- El nombre original se conserva en memoria (`_state["excel_name"]`, `_state["csv_name"]`) y `/api/ping` lo devuelve como `excel_name` / `csv_name`, para que no se pierda al recargar la página.
- Aviso “Uso administrativo” como footnote de grupo con icono de advertencia, no como caja amarilla.
- Diagnóstico PWA dentro de `<details>` “Avanzado” como filas de ajustes:
  - Versión del servidor.
  - Estado del service worker.
  - Modo offline.
  - Botones “Limpiar caché” y “Recargar” de 44 px.
- No se muestra “PWA” como insignia en la vista principal.

### 11.9 Voucher de impresión

- Se conserva la estructura actual: marca, producto, PLU, descuento, precios y tres barcodes.
- El código de plan usa `plan_barcode`.
- Fondo blanco, texto negro, barcode con borde punteado.
- Tipografía del sistema para el texto y mono para los códigos; sin cambios en el formato físico salvo espaciado para que quepa en una página.

## 12. Estados

Cada vista debe implementar estos estados:

| Estado | Cuándo | Qué muestra |
|---|---|---|
| Cargando | Fetch en curso | Skeleton de 3 filas/tarjetas; no spinner global |
| Sin datos | `/api/ping` con `excel: null` | “No hay precios cargados” + “Ir a Configuración” |
| Inicial | Sin query, operadora ni filtros | “Escanea o busca un equipo” + pasos |
| Sin resultados | Query/filtros con 0 resultados | “No encontramos ese producto” + “Limpiar filtros” |
| Error de red | Fetch falla | “No pudimos conectar” + “Reintentar” |
| Offline | `navigator.onLine === false` o API 503 offline | Banner ámbar + última búsqueda si existe; si no, “Sin conexión” + reintentar |
| Éxito al copiar | Clipboard OK | Toast “Código copiado” con `role="status"` |
| Error al copiar | Clipboard falla | Toast “No se pudo copiar” + `role="alert"` |

## 13. Comportamiento y datos

### Encabezado y vigencia

- `/api/stats` agrega `desde` y `hasta` con la fecha mínima y máxima del catálogo cargado.
- El subtítulo del header se genera como “Semana 45 · 11–17 nov” a partir de esas fechas; si no hay datos, muestra “Sin precios cargados”.
- La semana usa la convención del archivo: `ceil(día_del_año / 7)`. Para `2026-11-11` eso da 45, igual que el nombre `W45` del Excel.
- No se hardcodea el número de semana ni el rango de fechas.
- Si el Excel cambia de semana, el header se actualiza al recargar los datos.

### Búsqueda

- Debounce de 300 ms.
- Enter ejecuta de inmediato.
- Después de una búsqueda, el foco vuelve al input para permitir escaneo continuo.
- Al cambiar operadora, marca o filtros, se resetea la paginación a la primera página.
- La búsqueda vacía no consulta el catálogo completo salvo que el usuario pulse “Ver todo el catálogo”.

### Paginación

- Client-side sobre el resultado de `/api/search`, que sigue devolviendo el arreglo completo.
- Tamaño: 40 móvil, 50 escritorio.
- “Cargar más” agrega la siguiente página sin destruir el foco.
- El contador usa `aria-live="polite"`.

### Render por layout

- `matchMedia('(min-width: 1024px)')` decide si se renderiza tabla o lista.
- Al cruzar el breakpoint se vuelve a renderizar la vista activa.
- Nunca se generan simultáneamente 712 tarjetas y 712 filas.

### Selección

- Móvil: al tocar una fila se abre el detalle a pantalla completa.
- Escritorio: al hacer click o Enter en “Ver códigos” se actualiza el panel.
- El detalle conserva el producto seleccionado al paginar si sigue en la lista.
- Escape cierra el detalle y devuelve el foco al botón que lo abrió.

### Datos de códigos

- Equipo: `ean13 || plu_cod`.
- Plan: `plan_barcode`.
- PLU: `plu_cod`.
- Si falta el código de plan, la tarjeta muestra “Sin código de plan” y no renderiza una imagen rota.
- Si falta el EAN, se muestra el PLU como fallback y se indica “Calculado” o “Sin código”.
- El texto “formula” se reemplaza por “Calculado”.

### Barcode en pantalla

- `/api/barcode-inline/<code>?text=0` devuelve el SVG sin texto embebido para las tarjetas de pantalla.
- El número se muestra debajo en HTML, seleccionable y copiable.
- Se aumenta el quiet zone a 4 módulos para mejorar la lectura.
- Fondo blanco puro, barras negras, sin bordes redondeados dentro del área del código.

## 14. Accesibilidad

- `meta viewport` sin `maximum-scale` ni `user-scalable=no`.
- Todo control interactivo es `<button>`, `<a>`, `<input>`, `<select>` o tiene `role` + `tabindex="0"` + manejo de Enter/Espacio.
- Los `div` y `tr` con `onclick` se eliminan o se convierten en botones.
- Foco visible en todos los controles: `outline: 2px solid #0066CC; outline-offset: 2px`.
- El detalle móvil usa `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, foco inicial en “Volver” o en el título, trampa de foco y restauración al cerrar.
- El filtro móvil también es un diálogo con las mismas reglas.
- El botón de cerrar tiene `aria-label="Cerrar"`.
- Los toasts usan `role="status"` para éxito y `role="alert"` para error.
- El contador de resultados usa `aria-live="polite"` y anuncia “40 de 712 productos”.
- Las operadoras se identifican con texto además del color.
- Los iconos decorativos llevan `aria-hidden="true"`.
- Los barcodes tienen `alt` descriptivo: “Código de barras del equipo” y “Código de barras del plan CLARO”.
- El foco no queda oculto por el header o el footer fijos: `scroll-padding-top` y `scroll-padding-bottom`.
- Se respeta `prefers-reduced-motion`; las transiciones se reducen a 0–100 ms.
- Contraste mínimo 4.5:1 para texto normal y 3:1 para texto grande y elementos de UI.

## 15. Rendimiento

- Sin Tailwind CDN ni framework CSS. CSS propio en `static/app.css`; el proyecto no tiene paso de build.
- Sin fuentes web: la pila del sistema evita descargas y parpadeo tipográfico.
- CSS y JS se precachean en el service worker.
- Solo se renderiza la vista activa.
- 40–50 resultados por página.
- Imágenes de barcode solo en el detalle, no en la lista.
- `loading="lazy"` y `decoding="async"` en imágenes de barcode.
- No se re-renderiza toda la lista en cada tecla; se espera el debounce.
- Objetivo: menos de 2.500 nodos DOM con 40 resultados.
- Objetivo: primera búsqueda percibida en menos de 300 ms en local; en Vercel depende de la red.
- Se elimina el `autofocus` que abre el teclado en móvil sin intención; en escritorio se mantiene. En móvil, el input se enfoca al tocar.

## 16. PWA y offline

- `CACHE_NAME = 'retailpos-v3'` y `BARCODE_CACHE = 'retailpos-barcodes-v3'`.
- `APP_SHELL` incluye `/`, `/static/app.css`, `/static/app.js`, `/manifest.json`, `/static/icons/icon-192.png` y `/static/icons/icon-512.png`.
- Navegación network-first; assets cache-first; API network-first con fallback.
- El fallback offline de API responde 503 con `offline: true`; no se cachean errores.
- Los últimos resultados exitosos se conservan para consulta offline; no se promete búsqueda nueva sin red.
- `manifest.json` actualiza `background_color` y `theme_color` a `#F2F2F7`, `lang` a `es-CL` y conserva los atajos `?op=`.
- Se generan iconos 192×192 y 512×512 con zona segura maskable.
- El banner offline usa fondo ámbar y texto oscuro con contraste AA.
- La app debe abrir desde el icono instalado y mostrar el shell aunque no haya red.

## 17. Responsive

| Ancho | Comportamiento |
|---|---|
| 360–430 px | Una columna, bottom nav, detalle a pantalla completa, códigos apilados |
| 431–767 px | Una columna, cards más anchas, mismos códigos apilados |
| 768–1023 px | Tabla simple o lista ancha; sin panel lateral; detalle a pantalla completa |
| 1024–1440 px | Split 7/5, panel sticky, tabla de 6 columnas, header con nav |

- Sin scroll horizontal en 360, 768, 1024 y 1440 px.
- Respetar `safe-area-inset-bottom` en iOS.
- El contenido nunca queda tapado por header o bottom nav.

## 18. Copy de interfaz

- Título: “Precios y códigos”.
- Subtítulo: “Semana 45 · 11–17 nov”.
- Placeholder: “Escanea el código o busca…”.
- Estado inicial: “Escanea o busca un equipo”.
- Pasos: “Escanea el código del equipo”, “Revisa el descuento”, “Muestra el código del plan”.
- Código 1: “Código del equipo”.
- Código 2: “Código del plan · CLARO”.
- Botón: “Copiar código” → “Copiado”.
- Impresión: “Imprimir códigos”.
- Sin datos: “No hay precios cargados”.
- Sin resultados: “No encontramos ese producto”.
- Error: “No pudimos conectar”.
- Offline: “Sin conexión — mostrando datos guardados”.

## 19. Criterios de aceptación

1. Al abrir la app sin query ni filtros, no se muestran 712 productos; se muestra el estado “Escanea o busca un equipo”.
2. Con 40 resultados visibles, el DOM total es menor a 2.500 nodos.
3. Solo se renderiza la lista móvil o la tabla de escritorio, nunca ambas.
4. En 390×844, el detalle muestra los dos barcodes completos sin scroll, en orden Equipo → Plan.
5. Todos los controles interactivos miden al menos 44×44 px.
6. Lighthouse Accessibility ≥ 95 y cero fallos de contraste.
7. Se puede buscar, abrir un producto, copiar ambos códigos, imprimir y cerrar usando solo teclado.
8. El zoom del navegador funciona en móvil.
9. Si `/api/ping` devuelve `excel: null`, se ve “No hay precios cargados” y un botón a Configuración.
10. Si una búsqueda no tiene resultados, se ve “No encontramos ese producto” y “Limpiar filtros”.
11. No hay scroll horizontal en 360, 768, 1024 y 1440 px.
12. El voucher imprime los tres códigos y el plan usa `plan_barcode`.
13. La PWA instalada recibe la versión nueva (`retailpos-v3`), abre offline y conserva la última búsqueda exitosa; una búsqueda nueva sin red muestra “Sin conexión” y no “sin resultados”.
14. `python -m pytest -q` pasa completo.
15. El HTML no carga `cdn.tailwindcss.com`, no carga Google Fonts y no usa emojis como iconos.
16. El manifest referencia iconos que existen y se sirven con 200.
17. Un atajo `/?op=CLARO` abre la app con el chip CLARO activo y el catálogo filtrado.
18. El subtítulo de semana se genera desde `desde`/`hasta` del Excel y no está hardcodeado.
19. Los nombres originales de Excel/CSV se mantienen visibles tras recargar la página.

## 20. Pruebas

### Automáticas

- Tests existentes de `plan_barcode` (columna D) y PWA, actualizados a verificaciones estructurales o de comportamiento. No se exige que las aserciones de texto exacto del HTML viejo sobrevivan a la reescritura; sí se exige que el contrato `plan_barcode` y la estrategia network-first sigan cubiertos.
- Nuevo test: `/` responde 200 y contiene `/static/app.css` y `/static/app.js`, no `cdn.tailwindcss.com`.
- Nuevo test: `static/app.css` existe y no está vacío.
- Nuevo test: `/manifest.json` referencia iconos existentes.
- Nuevo test: `sw.js` contiene `retailpos-v3` y `/static/app.css` + `/static/app.js` en `APP_SHELL`, y el fallback offline de API usa 503 con `offline: true`.
- Nuevo test: `/api/search` devuelve `plan_barcode` distinto de `plan` para un fixture.
- `python -m pytest -q`.

### Manuales

- Lighthouse en local con datos reales.
- Navegación completa solo con teclado.
- Lectura de barcodes con escáner físico en pantalla de teléfono y en voucher impreso.
- Prueba en 360, 390, 430, 768, 1024 y 1440 px.
- Prueba offline: cargar una vez, activar avión, recargar.
- Prueba de instalación PWA y actualización de cache.
- Prueba de copiado en HTTP local y HTTPS de Vercel.

## 21. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| El barcode en pantalla no se lee bien con el escáner | Alto | Barcode ancho, alto, quiet zone 4, fondo blanco puro, probar con hardware; mantener impresión |
| El tema claro pierde identidad de marca | Medio | Usar colores de operadora accesibles y tipografía consistente |
| La reescritura rompe el flujo de impresión | Alto | Conservar el contenedor y probar `window.print()` antes de cerrar |
| Vercel no persiste el Excel | Medio | Estado “No hay precios cargados” claro y botón a Configuración |
| El CSS propio se desincroniza de las clases generadas por JS | Medio | Usar clases estáticas y cubrirlas con un test estructural |
| La PWA sigue mostrando la versión vieja | Medio | Subir cache a v3 y verificar `sw.js` en producción |
| El cambio es muy grande para una sola entrega | Medio | Implementar por fases: shell + búsqueda, detalle, stats/config, PWA |

## 22. Fases de implementación

1. **Base visual y shell:** CSS propio, tokens, header, navegación, estados, iconos.
2. **Buscar:** estado inicial, búsqueda, filtros, paginación, lista móvil y tabla de escritorio.
3. **Detalle / Modo escaneo:** panel móvil y escritorio, barcode cards, copiado, impresión.
4. **Stats y Config:** rediseño, estados, diálogos.
5. **PWA y cierre:** manifest, iconos, SW v3, pruebas, Lighthouse, validación en Vercel.

Cada fase debe dejar la app funcionando y testeable.

## 23. Decisiones resueltas en la revisión

- **Backend aditivo:** permitido para `?text=0`, `quiet_zone`, fechas en `/api/stats` y nombres originales en `/api/ping`. No se cambia el contrato existente.
- **Semana dinámica:** el header usa `desde`/`hasta` del catálogo; no se hardcodea.
- **Tests viejos:** se actualizan a verificaciones estructurales o de comportamiento; no se exige conservar aserciones de texto exacto del HTML anterior.
- **Operadora:** el segmented control sigue siendo un filtro primario debajo de la búsqueda y se lee `?op=` para los atajos del manifest.
- **Nombre de archivo:** se conserva en memoria y se devuelve en `/api/ping`; tras recargar se muestra el nombre original.
- **Tipografía:** pila del sistema para UI y `ui-monospace` para códigos; sin fuentes web.
- **Estilo iOS:** listas agrupadas, segmented control, barras translúcidas, large titles, sheet con grabber e indicador de inicio.
- **Iconos:** SVG inline estilo SF Symbols; sin emojis.
- **Tailwind:** compilado con CLI y commiteado; sin CDN en runtime.
- **Copiar descuento:** queda como acción secundaria de 44 px en el resumen del detalle, no en la cabecera de códigos.
- **Paginación:** 40 móvil, 50 escritorio; ajustable solo si las pruebas de rendimiento lo justifican.
- **Enlaces profundos:** no son obligatorios; si se agregan, no deben romper el flujo de escaneo.
- **Animación:** transición de 180–220 ms, reducida a 0–100 ms con `prefers-reduced-motion`.

## 24. Decisión offline: shell + última búsqueda

El usuario eligió la opción 1.

- La PWA abre sin red y muestra el shell completo con el banner “Sin conexión — mostrando la última búsqueda”.
- Se conservan los últimos resultados exitosos en memoria y en caché; el vendedor puede seguir abriendo esos productos y mostrando sus códigos.
- Una búsqueda nueva sin red no se presenta como “sin resultados”. Muestra un estado de error de conexión con “Reintentar”.
- No se agrega endpoint de catálogo ni búsqueda local sobre los 712 productos.
- El fallback offline del service worker responde **503** con `{ "error": "Sin conexión", "offline": true }`, no 200, para que la app distinga “sin red” de “sin resultados”.
- El service worker no cachea respuestas 503 ni respuestas de error.
- Si no hay resultados previos y no hay red, el estado es “Sin conexión” con opción de reintentar; no se muestra el estado inicial como si hubiera datos.

## 25. Aprobación

Este documento requiere aprobación explícita antes de escribir código de producto. Al aprobarlo, el siguiente paso es crear el plan de implementación con `superpowers:writing-plans`.
