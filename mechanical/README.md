# DStat-RD / Diseño Mecánico

Este directorio almacena todos los recursos relacionados con el diseño mecánico, gabinete, soportes y piezas de montaje para el instrumento.

---

## 📂 Organización de Carpetas

```text
mechanical/
├── cad/         # Archivos de diseño originales (FreeCAD, Fusion 360, SolidWorks, etc.)
├── step/        # Modelos en formato STEP (.step / .stp) neutral para interoperabilidad
├── stl/         # Mallas exportadas para impresión 3D (.stl / .3mf)
├── renders/     # Renders fotorrealistas de la carcasa y ensambles
└── README.md    # Esta documentación
```

---

## 🖨️ Recomendaciones de Fabricación e Impresión 3D

- **Materiales sugeridos:** PETG, ABS o ASA para mayor resistencia térmica y química; PLA para prototipado rápido.
- **Altura de capa recomendada:** 0.20 mm.
- **Relleno (Infill):** 20% a 30% giroidal o cuadrícula.
- **Tolerancias mecánicas:** Considerar una tolerancia de 0.2 mm a 0.3 mm para las ranuras laterales de deslizamiento de la PCB y las ventanas de conectores BNC y USB.
- **Hardware de fijación:** Tornillos roscados directamente sobre los alojamientos de la pieza impresa en 3D (diseño optimizado sin necesidad de insertos metálicos). La PCB queda retenida por correderas sin tornillos.
