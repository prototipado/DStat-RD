# Solución de Problemas (Troubleshooting) - DStat-RD

Guía de resolución de fallas frecuentes en hardware, firmware y software.

---

## 🔍 Problemas Comunes y Soluciones

### 1. El puerto serie no aparece o no se reconoce el dispositivo
- **Causa probable:** Cable USB defectuoso o de solo carga (sin líneas D+/D-).
- **Acción:** Cambiar por un cable USB con capacidad de transmisión de datos. En Windows, revisar el Administrador de Dispositivos; en Linux, ejecutar `dmesg | tail` o `ls /dev/ttyACM*`.

### 2. El microcontrolador queda bloqueado en modo DFU
- **Causa:** El firmware no arranca, o la línea de selección de bootloader quedó retenida en bajo / se activó una secuencia de rescate.
- **Acción:**
  - Verificar tensiones en los rieles de alimentación (+3.3V, +5V, ±V analógico).
  - Volver a flashear el firmware utilizando `dfu-util` o el programador ISP correspondiente.
  - Asegurar que no haya restos de estaño o puentes en los pines de reset y modo bootloader.

### 3. Mediciones con exceso de ruido de 50/60 Hz
- **Causa:** Interferencia capacitiva o inductiva de la red eléctrica en los cables de los electrodos.
- **Acción:**
  - Utilizar cables coaxiales o blindados para el electrodo de trabajo (WE).
  - Alojar la celda electroquímica dentro de una caja metálica conectada a masa (Jaula de Faraday).
  - Verificar que la fuente de alimentación no introduzca rizado excesivo.

### 4. Lecturas saturadas o en fondo de escala
- **Causa:** Rango de ganancia TIA demasiado alto para la corriente generada, o circuito abierto en los electrodos.
- **Acción:** Seleccionar un rango de corriente más amplio en la GUI o revisar la continuidad física de los electrodos en la solución.
