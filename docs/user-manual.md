# Manual de Usuario - DStat-RD

Guía completa para la configuración y operación del potenciostato mediante la GUI.

---

## 1. Conexión Inicial

1. Conectar el instrumento al puerto USB del ordenador.
2. Iniciar la aplicación ejecutando `python main.py` desde la carpeta `gui/`.
3. Seleccionar el puerto COM / tty correspondiente en la barra de conexión y hacer clic en **Conectar**.

---

## 2. Técnicas Disponibles

### Voltamperometría Cíclica (CV)
- **V_start (V):** Potencial de partida.
- **V_apex1 / V_apex2 (V):** Potenciales de inversión de barrido.
- **Scan rate (V/s):** Velocidad de barrido.
- **Cycles:** Número de ciclos completos.

### Voltamperometría de Onda Cuadrada (SWV)
- **V_start / V_stop (V):** Rango de potencial.
- **Step height (V):** Altura de escalón.
- **Pulse height (V):** Amplitud de pulso.
- **Frequency (Hz):** Frecuencia de modulación.

### Cronoamperometría (CA)
- **Potential steps (V):** Escalones de potencial aplicados.
- **Duration (s):** Tiempo de aplicación por escalón.

---

## 3. Adquisición y Exportación de Datos

- Los gráficos se actualizan en tiempo real durante la medición.
- Al finalizar, se pueden exportar los datos crudos a formatos estándar (.csv, .tsv) y capturas gráficas (.png, .svg).
