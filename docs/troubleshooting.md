# Solución de Problemas (Troubleshooting) - DStat-RD

Guía de resolución de fallas frecuentes en hardware, firmware y software.

---

## 🔍 Problemas Comunes y Soluciones

### 1. El puerto serie no aparece o figura con error (Triángulo Amarillo en Windows)
- **Causas comunes:**
  - Cable USB defectuoso o de solo carga (sin líneas D+/D-).
  - Windows no asignó automáticamente el controlador serie CDC ACM correspondiente al microcontrolador AVR/XMega.
- **Acción inicial:** Comprobar que el cable USB transmita datos. En Linux, verificar con `ls /dev/ttyACM*` o `dmesg | tail`. En Windows, abrir el **Administrador de Dispositivos** (`devmgmt.msc`) y seguir la guía detallada a continuación si el dispositivo figura con un triángulo amarillo.

---

## 🛠️ Procedimiento: Solución de Controlador COM en Windows

Si al conectar el potenciostato Windows muestra una advertencia en el puerto serie, seguir estos pasos para forzar la asignación del controlador correcto:

### Paso 1: Identificar el dispositivo en conflicto
En el **Administrador de dispositivos**, desplegar la categoría **Puertos (COM y LPT)**. El instrumento figurará como `AVR MEGA Virtual Com Port (COMxx)` acompañado de un icono triangular amarillo de advertencia.

<p align="center">
  <img src="../assets/diagrams/usb_1.png" alt="Dispositivo con advertencia" width="450" />
</p>

---

### Paso 2: Iniciar actualización de controlador
Hacer clic derecho sobre el dispositivo con advertencia y seleccionar **Actualizar controlador**.

<p align="center">
  <img src="../assets/diagrams/usb_2.png" alt="Menú contextual Actualizar controlador" width="450" />
</p>

---

### Paso 3: Buscar controladores en el equipo
En la ventana del asistente, hacer clic sobre la opción **Examinar mi PC en busca de controladores** (búsqueda e instalación manual).

<p align="center">
  <img src="../assets/diagrams/usb_3.png" alt="Examinar mi PC en busca de controladores" width="550" />
</p>

---

### Paso 4: Elegir desde la lista de controladores disponibles
Seleccionar la opción inferior: **Elegir en una lista de controladores disponibles en el equipo**.

<p align="center">
  <img src="../assets/diagrams/usb_4.png" alt="Elegir en una lista de controladores disponibles" width="550" />
</p>

---

### Paso 5: Seleccionar el controlador compatible
Asegurarse de que esté marcada la casilla **Mostrar el hardware compatible**. En la lista de modelos, seleccionar **AVR MEGA Virtual Com Port** y presionar **Siguiente**.

<p align="center">
  <img src="../assets/diagrams/usb_5.png" alt="Seleccionar AVR MEGA Virtual Com Port" width="550" />
</p>

---

### Paso 6: Confirmación de instalación
Windows completará el enlace del controlador y desplegará el mensaje *"Windows actualizó correctamente los controladores"*. Presionar **Cerrar**.

<p align="center">
  <img src="../assets/diagrams/usb_6.png" alt="Windows actualizó correctamente los controladores" width="550" />
</p>

---

### Paso 7: Verificación final
En el Administrador de dispositivos, el puerto figurará activo y sin signos de advertencia (`AVR MEGA Virtual Com Port (COMxx)`). El instrumento ya se encuentra listo para ser seleccionado en la GUI de DStat.

<p align="center">
  <img src="../assets/diagrams/usb_7.png" alt="Puerto COM reconocido correctamente" width="450" />
</p>

---

### 2. El microcontrolador queda bloqueado en modo DFU
- **Síntoma en Windows:** En el Administrador de dispositivos no figura ningún puerto COM, sino una entrada bajo **Microchip Tools** (o *Atmel USB Devices*) identificada como **`ATxmega256A3U`**:

<p align="center">
  <img src="../assets/diagrams/dfu_1.png" alt="Microcontrolador detectado en modo DFU" width="450" />
</p>

- **Causa:** El firmware principal no arranca (firmware corrupto o memoria borrada), o la línea de selección de bootloader quedó retenida en nivel bajo (forzando el arranque del bootloader USB de fábrica).
- **Acción:**
  - Verificar tensiones en los rieles de alimentación (+3.3V, +5V, ±V analógico).
  - Volver a flashear el archivo de firmware `.hex` utilizando `dfu-util` o Atmel FLIP:
    ```bash
    dfu-util -d 03eb:2fe2 -a 0 -D dstat-firmware.hex
    ```
  - Asegurar que no haya restos de soldadura, estaño o puentes en los pines de reset y modo bootloader.

### 3. Mediciones con exceso de ruido de 50/60 Hz
- **Causa:** Interferencia capacitiva o inductiva de la red eléctrica en los cables de los electrodos.
- **Acción:**
  - Utilizar cables coaxiales o blindados para el electrodo de trabajo (WE).
  - Alojar la celda electroquímica dentro de una caja metálica conectada a masa (Jaula de Faraday).
  - Verificar que la fuente de alimentación no introduzca rizado excesivo.

### 4. Lecturas saturadas o en fondo de escala
- **Causa:** Rango de ganancia TIA demasiado alto para la corriente generada, o circuito abierto en los electrodos.
- **Acción:** Seleccionar un rango de corriente más amplio en la GUI o revisar la continuidad física de los electrodos en la solución.
