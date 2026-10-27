# Guía de Montaje Mecánico - DStat-RD

Instrucciones para el ensamblado físico de la electrónica dentro del gabinete impreso en 3D.

---

## 🛠️ Herramientas y Materiales Requeridos

- **Piezas impresas en 3D** (archivos listos en [`mechanical/stl/`](../mechanical/stl/)):
  - Base inferior con guías laterales (`bottom.stl`).
  - Tapa superior de cierre (`top.stl`).
  - Panel frontal para conectores BNC (`bnc.stl`).
  - Panel posterior para conector USB (`usb.stl`).
- **Tornillos métricos:** Roscados **directamente en el plástico** de la pieza impresa (diseño simplificado sin necesidad de insertos térmicos de latón).
- **Destornillador:** Según la cabeza de los tornillos empleados (Allen o Phillips).
- **Batea de ultrasonido y alcohol isopropílico (IPA)** de alta pureza (≥ 99.5%).

---

## 📦 Proceso de Ensamblaje Paso a Paso

### Paso 1: Limpieza previa por ultrasonido (Mandatorio)
> [!IMPORTANT]
> **Paso crítico para la exactitud del instrumento:**  
> Antes de introducir la placa en el gabinete, sumergir la PCB soldada en una **batea de ultrasonido con alcohol isopropílico (IPA)** durante 5 a 10 minutos y secar minuciosamente con aire comprimido tibio. Los residuos de flux de soldadura conducen corrientes de fuga parásitas que provocan errores de medición de hasta más del 70% en el rango de nanoamperios (ver [Reporte de Caracterización](../docs/characterization/chronoamperometry.md)).

---

### Paso 2: Preparación de la base inferior
- Tomar la pieza base (`bottom.stl`) y verificar que las **ranuras guía longitudinales** a ambos lados estén libres de rebabas o hilos de impresión para permitir que los bordes de la PCB deslicen con suavidad y sin atascos.

---

### Paso 3: Deslizamiento y encastre de la PCB (Sin tornillos en la placa)
- **La PCB no se fija con tornillos:** se monta mediante un sistema de corredera.
- Tomar la PCB limpia e introducir sus bordes laterales en las ranuras de la base inferior (`bottom.stl`).
- Deslizar la placa suavemente hacia adelante hasta que **haga tope firme en el extremo de los conectores BNC**.
- Al llegar al tope frontal:
  - Los conectores BNC quedan perfectamente asentados contra el frente.
  - El conector USB en el extremo posterior queda alineado de forma natural y a la altura exacta requerida para el puerto de datos/alimentación.

---

### Paso 4: Montaje de paneles frontal y posterior
- Colocar el panel frontal de los BNC (`bnc.stl`) y el panel posterior USB (`usb.stl`) en sus respectivos encajes y rebajes de la base.

---

### Paso 5: Colocación de la tapa superior y fijación
- Posicionar la tapa superior (`top.stl`) sobre el ensamble, asegurando que cierre parejo sobre los paneles frontal y trasero y la base.
- Colocar los tornillos perimetrales y enroscarlos **directamente en los orificios del plástico impreso**.
- **Recomendación:** Ajustar los tornillos de manera firme pero progresiva, sin aplicar torque excesivo para no barrer la rosca en el material termoplástico.
