# RetailPOS Pro 📱

Dashboard progresivo (PWA) de ventas con planes de telefonía (**CLARO**, **WOM**, **ENTEL**) para agilizar el pistoleo en caja de retail y calcular automáticamente los descuentos por operador y códigos de barra.

---

## 🚀 Características Principales

1. **Mobile-First PWA:**
   - Diseñado específicamente para pantallas móviles y lectores portátiles.
   - Totalmente operable sin conexión gracias a Service Worker y Manifest.
   - Bottom Sheet deslizable para pistolear o visualizar detalles.

2. **Cálculo Automático de Códigos de Barra EAN-13:**
   - Deducción matemática validada contra existencias reales:
     $$\text{base12} = \text{"020002"} + \text{PLU}[1:7]$$
     $$\text{EAN-13} = \text{base12} + \text{check\_digit\_EAN13}$$
   - Generación SVG nítida en vivo para:
     - **Código de Barra del Equipo (EAN-13)**
     - **Código de Barra del Plan Operador (PLAN)**
     - **PLU Interno**
   - Botón directo para **Copiar Descuento** numérico limpio para la caja registradora.

3. **Gestión Dinámica de Archivos:**
   - Carga y actualización del Excel de precios semanal desde la interfaz.
   - Carga y actualización del archivo CSV de existencias como respaldo de códigos.

---

## 🛠️ Ejecución Local

1. Clona el repositorio:
   ```bash
   git clone https://github.com/mashmellows172-cmd/retail-pos.git
   cd retail-pos
   ```
2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecuta la aplicación:
   - En Windows: doble clic en `launch.bat`
   - O vía terminal:
     ```bash
     python app.py
     ```
4. Abre en tu navegador: `http://localhost:5050`

---

## ☁️ Despliegue en Vercel

Configurado con `vercel.json` y endpoints Serverless en Python listos para importar desde GitHub.
