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

1. Conectar la celda dummy adecuada.
2. Desde la GUI, acceder a la pestaña o ventana de **Calibración**.
3. Ejecutar la rutina automática de barrido de offset y ganancia.
4. Verificar que la pendiente I vs. V cumpla con la Ley de Ohm ($I = V / R$).
5. Guardar los coeficientes resultantes en el perfil de calibración del instrumento.
