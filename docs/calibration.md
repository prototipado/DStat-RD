# Procedimiento de Calibración - DStat-RD

Pasos para verificar y calibrar las etapas de ganancia de corriente (TIA) y los convertidores DAC/ADC del instrumento.

---

## 🎯 Objetivo

Asegurar la exactitud en la aplicación de potenciales y en la medición de corrientes a través de los diferentes rangos del amplificador de transimpedancia (TIA).

---

## 🧪 Celda de Prueba (Dummy Cell)

Para calibración y verificación funcional se recomienda una celda simulada con resistencias de precisión (tolerancia 0.1% o mejor):
- **Rango 1:** Resistencia de 100 kΩ entre WE y CE/RE.
- **Rango 2:** Resistencia de 1 MΩ entre WE y CE/RE.
- **Rango 3:** Resistencia de 10 kΩ entre WE y CE/RE.

---

## 📋 Pasos de Calibración

> [!IMPORTANT]
> **Condición previa de hardware (Limpieza de PCB):**  
> Antes de realizar cualquier calibración de ganancia u offset del TIA, asegúrese de que la placa haya sido **lavada en batea de ultrasonido con alcohol isopropílico (IPA)** para eliminar todo resto de flux de soldadura. Los residuos de flux introducen corrientes de fuga parásitas de hasta decenas de nanoamperios que falsean la respuesta lineal en corrientes bajas (ver [Caracterización](./characterization/chronoamperometry.md)).

1. Conectar la celda dummy adecuada.
2. Desde la GUI, acceder a **View → Calibration / Device Settings…**.
3. Presionar **Read from device** para obtener los coeficientes actuales grabados en la EEPROM.
4. Ajustar el offset del DAC y los trims de ganancia TIA contrastando contra la corriente teórica por Ley de Ohm ($I = V / R$).
5. Presionar **Write to device** para almacenar los coeficientes calibrados de forma persistente.
