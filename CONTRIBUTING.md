# Guía de Contribución (CONTRIBUTING)

¡Agradecemos tu interés en colaborar con **DStat-RD**! Para mantener la consistencia y calidad técnica del proyecto, te pedimos seguir las siguientes pautas.

---

## 💻 Contribución al Código (GUI y Firmware)

1. **Estilo de código:**
   - Para Python (GUI): Adherir a las normas [PEP 8](https://peps.python.org/pep-0008/). Se recomienda usar `flake8` o `ruff` y formateador `black`.
   - Nombres de variables y funciones descriptivos en inglés o español consistente según el módulo.
2. **Modularidad:** Separar estrictamente la lógica de comunicación con el hardware (`core/`) de la presentación de la interfaz gráfica (`views/`).
3. **Manejo de errores:** Evitar capturar excepciones genéricas silenciosas (`except:` sin logueo); reportar adecuadamente fallas de conexión o desconexión USB inesperada.

---

## 📐 Contribución a Modelos CAD y Mecánica

1. **Formatos obligatorios:**
   - Todo cambio o nueva pieza debe incluir su archivo fuente original en `mechanical/cad/` (e.g., `.FCStd`, `.f3d`, `.sldprt`).
   - Debe adjuntarse una exportación en formato neutral **STEP** (`.step` o `.stp`) en `mechanical/step/`.
   - Si la pieza es imprimible en 3D, incluir la malla exportada en **STL** (`.stl`) orientada en la posición óptima de impresión en `mechanical/stl/`.
2. **Nomenclatura de archivos:**
   - Usar nombres descriptivos en minúsculas separados por guiones: `ejemplo-carcasa-inferior_v1.step`.
   - Incluir versión o sufijo si reemplaza una pieza anterior.

---

## 📝 Contribución a la Documentación

1. **Formato:** Todos los documentos deben redactarse en Markdown estándar con codificación UTF-8.
2. **Imágenes:** Guardar capturas o fotos en `assets/` y referenciarlas con rutas relativas.
3. **Claridad:** Mantener pasos secuenciales numerados y advertencias destacadas para operaciones delicadas (como calibración o conexión de voltajes).

---

## 🔀 Flujo de Trabajo con Git

1. Crear un branch para tu característica o corrección:
   ```bash
   git checkout -b feature/nueva-funcionalidad
   # o
   git checkout -b fix/problema-usb
   ```
2. Realizar commits claros y descriptivos:
   ```bash
   git commit -m "feat(gui): agrega selector dinámico de tasa de baudios"
   ```
3. Enviar un Pull Request (PR) detallando los cambios realizados, pruebas ejecutadas y capturas si aplica.
