<p align="center">
  <img src="assets/covers/dstat_logo.png" alt="DStat-RD Logo" width="180" />
</p>

<h1 align="center">DStat-RD</h1>

<p align="center">
  <strong>Potenciostato / Galvanostato de código abierto</strong> basado en la plataforma DStat, adaptado y modernizado para investigación, docencia y aplicaciones de laboratorio.
</p>

---

## 📋 Tabla de Contenidos

- [Presentación](#presentación)
- [Características Principales](#características-principales)
- [Galería](#galería)
- [Estructura del Repositorio](#estructura-del-repositorio)
- [Instalación y Puesta en Marcha](#instalación-y-puesta-en-marcha)
- [Documentación](#documentación)
- [Atribución y Créditos](#atribución-y-créditos)
- [Licencia](#licencia)

---

## 🔬 Presentación

**DStat-RD** es una evolución y actualización de la plataforma de instrumentación electroquímica de bajo costo y hardware abierto **DStat**. Este repositorio centraliza la interfaz gráfica de usuario (GUI), el diseño mecánico de la carcasa y accesorios, la documentación de montaje y calibración, y las guías de uso del instrumento.

---

## ✨ Características Principales

- **Técnicas electroquímicas soportadas:**
  - Voltamperometría Cíclica (CV)
  - Voltamperometría de Onda Cuadrada (SWV)
  - Voltamperometría de Pulso Diferencial (DPV)
  - Cronoamperometría (CA)
  - Espectroscopía de Impedancia Electroquímica (EIS) *(según soporte de hardware)*
- **Interfaz Gráfica Moderna:** Control de parámetros, adquisición en tiempo real y exportación de datos.
- **Gabinete y Montaje Mecánico:** Diseño modular impreso en 3D con archivos CAD/STEP disponibles para réplica y modificación.
- **Conectividad:** Comunicación serie/USB con protocolo abierto.

---

## 📸 Galería

| Identidad / Software | Equipo y Carcasa | Captura de Interfaz (GUI) |
| :---: | :---: | :---: |
| <img src="assets/covers/dstat_logo.png" width="120" /> | *(Foto del equipo en `assets/photos/`)* | *(Captura de GUI en `assets/gui/`)* |

---

## 📁 Estructura del Repositorio

```text
├── gui/                      # Código fuente de la interfaz gráfica y dependencias
├── mechanical/               # Modelos CAD, STEP, STL para impresión 3D y planos
├── docs/                     # Manuales, montaje, conexión, calibración y caracterización
├── tools/                    # Utilidades y scripts de análisis de señales y validación
├── assets/                   # Fotografías, capturas de pantalla y diagramas
├── CONTRIBUTING.md           # Guía de contribución para código, CAD y docs
├── LICENSE                   # Licencia del proyecto
└── THIRD_PARTY_NOTICES.md    # Licencias de terceros y atribución del proyecto original
```

---

## 🚀 Instalación y Puesta en Marcha

### Prerrequisitos
- Python 3.10 o superior (recomendado).
- Controladores / permisos USB según el sistema operativo.

### Instalación de la GUI

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/prototipado/DStat-RD.git
   cd DStat-RD/gui
   ```

2. Crear y activar un entorno virtual:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux / macOS:
   source .venv/bin/activate
   ```

3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Ejecutar la aplicación:
   ```bash
   python main.py
   ```

---

## 📖 Documentación

Para consultar los manuales completos, visita la carpeta [`docs/`](./docs/):
- [Manual de Usuario](./docs/user-manual.md)
- [Guía de Montaje Mecánico y Carcasa](./docs/assembly.md)
- [Conexión al Instrumento](./docs/connection.md)
- [Procedimiento de Calibración](./docs/calibration.md)
- [Solución de Problemas (Troubleshooting)](./docs/troubleshooting.md)
- [Caracterización y Validación Experimental](./docs/characterization/README.md)

---

## 🤝 Atribución y Créditos

Este trabajo se basa y rinde homenaje al proyecto original **DStat**, desarrollado por el **Wheeler Microfluidics Lab** (Universidad de Toronto) y principalmente por **Michael D. M. Dryden**:

- **Proyecto Original:** [DStat Hardware & Software](https://github.com/dstat-dev) / [Wheeler Lab](https://microfluidics.utoronto.ca/)
- **Publicación científica:** Dryden, M. D. M., & Wheeler, A. R. (2015). *DStat: A Versatile, Open-Source Potentiostat for Electroanalysis and Integration*. PLoS ONE 10(10): e0140349.

Para detalles exhaustivos de licencias y créditos a terceros, consultar [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md).

---

## 📄 Licencia

El código propio y las modificaciones de este repositorio se distribuyen bajo los términos especificados en [`LICENSE`](./LICENSE) y [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md).
