# Guía de Montaje Mecánico - DStat-RD

Instrucciones para el ensamblado físico de las piezas del gabinete y la electrónica.

---

## 🛠️ Herramientas y Materiales Requeridos

- Piezas impresas en 3D (disponibles en [`mechanical/stl/`](../mechanical/stl/)).
- Soldador tipo cautín para inserción térmica de roscas.
- Insertos roscados M3 x 4mm (latón).
- Tornillos de cabeza cilíndrica Allen M3 x 6mm y M3 x 10mm.
- Destornillador hexagonal Allen de 2.5 mm.
- **Batea de ultrasonido y alcohol isopropílico (IPA)** de alta pureza (≥ 99.5%).

---

## 📦 Proceso de Ensamblaje

1. **Limpieza previa por ultrasonido (Crítico):**  
   > [!IMPORTANT]
   > Antes de montar la placa en el gabinete, sumergir la PCB armada en una **batea de ultrasonido con alcohol isopropílico (IPA)** durante 5–10 minutos y secar con aire comprimido tibio. Los residuos de flux de soldadura conducen microcorrientes que provocan errores de medición de hasta un 70% en el rango de nanoamperios (ver [Caracterización experimental](../docs/characterization/chronoamperometry.md)).
2. **Colocación de insertos:** Con el soldador a temperatura moderada (~220 °C), introducir los insertos de latón en los orificios correspondientes de la carcasa inferior y frontal.
3. **Montaje de la PCB:** Posicionar la placa DStat asegurando que los conectores USB y terminales de electrodos coincidan con los calados del panel.
4. **Fijación:** Asegurar la PCB utilizando tornillos M3 con arandelas plásticas para no dañar las pistas de masa.
5. **Cierre de gabinete:** Colocar la tapa superior y ajustar los tornillos perimetrales sin aplicar torque excesivo.
