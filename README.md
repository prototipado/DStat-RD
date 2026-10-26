# DStat GUI v2.1

Edición de escritorio Python 3 / Qt6 de la interfaz del DStat. Reutiliza el
protocolo serie y el código de experimentos más recientes, restaurando la
organización original de la ventana: ajustes del instrumento y controles de
experimento a la izquierda, autosave y cuaderno de datos a la derecha, y
controles de comunicación serial a lo largo de la parte inferior.

## Novedades de v2.1

- **Tema claro y oscuro** con selector en **View → Theme** (System / Light /
  Dark), persistente entre sesiones (QSettings).
- **Paleta consistente** con un único color de acento teal `#0d9488`, definida
  en `dstat_interface/core/interface/theme.py` y `styles.qss`.
- **Paneles tipo "card"** con bordes redondeados, espaciado y márgenes parejos.
- Botón **Execute** destacado en color de acento, **Stop** en rojo,
  **Connect/Disconnect** con estado visual claro.
- **Gráfico de matplotlib estilizado** según el tema (fondo, grilla sutil,
  línea más gruesa con acento), con iconos modernos en la barra de
  herramientas.
- **Panel Protocol** con fuente monoespaciada, colores por dirección y
  posibilidad de colapsarlo.
- Controles de entrada con estados hover/focus/disabled visibles.
- Barra de estado inferior con información útil.
- Mejor soporte de DPI alto y redimensionado de ventana.

## Ejecutar desde código fuente

Requiere Windows y Python 3.10 o superior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m dstat_interface.main
```

## Compilar el ejecutable de Windows

Desde un símbolo del sistema de Windows, ejecutá:

```bat
build_exe.bat
```

El script prefiere automáticamente el entorno virtual del workspace en
`..\.venv\Scripts\python.exe`, luego un `.venv` local y, por último, `python`
en el `PATH`. Para seleccionar otro intérprete, definí `PYTHON_EXE` antes de
ejecutar el script, por ejemplo:

```bat
set PYTHON_EXE=C:\path\to\python.exe
build_exe.bat
```

El script instala las dependencias de Python y PyInstaller, y crea una
aplicación onedir en `dist\DStat-GUI-dev2\`. Ejecutá
`DStat-GUI-dev2.exe` desde esa carpeta; mantené su directorio `_internal`
junto al ejecutable. El ejecutable no requiere que Python esté instalado en
la computadora de destino.

Los logs de ejecución y las trazas de fallos nativos se escriben en
`%LOCALAPPDATA%\DStat GUI 2.0\logs\` (`dstat-gui.log` y `crash.log`).

## Terminal de protocolo

El panel derecho muestra la conversación serial con el DStat mientras ocurre,
útil para revisar el protocolo de comandos:

| Color | Símbolo | Significado |
| --- | --- | --- |
| azul | `→` | línea enviada por la GUI (`!n`, el comando, parámetros, `a` para detener) |
| verde | `←` | línea recibida del DStat (`@ACK`, `@RCV`, `@DONE`, resultados) |
| gris | `·` | comentarios del firmware (`#...`) y notas de progreso |
| ámbar | `!` | respuesta inesperada; el comando se reintentó |
| rojo | `×` | comando que no pudo entregarse |

Los espacios finales se renderizan como `·` porque el firmware los cuenta con
`strlen()` y forman parte del prefijo de longitud. Las tramas binarias de
muestras no se registran (inundarían el panel); en su lugar se añade una
nota resumen cada 200 tramas. El panel se puede ocultar o restaurar con
**View → Protocol Terminal** (`Ctrl+P`), y su contenido se puede guardar en un
archivo de texto con **Save…**.

## Uso del instrumento

Conectá el DStat, hacé clic en **Refresh**, seleccioná su puerto COM y hacé
clic en **Connect**. La selección del puerto se muestra en la barra de
comunicación de ancho completo en la parte inferior de la ventana. Confirmá
el firmware/placa detectados en la barra de estado antes de ejecutar un
experimento.

## Técnicas incluidas

El motor Python 3 actual provee voltametría cíclica, voltametría de barrido
lineal, voltametría de onda cuadrada, voltametría de pulso diferencial,
cronoamperometría y potenciometría. La aplicación original Python 2/GTK
también listaba voltametría de CA, fotodiodo y calibración de offset; esos
modos no están implementados en el motor Python 3 reutilizado y no se
exponen aquí.

## Calibración

La GUI incluye un diálogo de calibración en **View → Calibration / Device
Settings…** que permite leer, editar y escribir los parámetros de la EEPROM
del DStat:

- Offset del DAC (`max5443_offset`).
- Trims de corriente por ganancia (`r100_trim` … `r100M_trim`).
- Constantes de calibración EIS (`eis_cal1`, `eis_cal2`).
- Sensor de luz (`tcs_enabled`, `tcs_clear_threshold`).
- Modo de unidades del DAC (`dac_units_true`).

Los valores se guardan en la EEPROM del DStat al pulsar **Write to device** y
persisten entre ciclos de encendido. **Restore defaults** restablece los
valores de fábrica del firmware.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Estructura del proyecto

```
dstat_interface/
  main.py                      # punto de entrada
  core/
    dstat/                     # comunicación serial, placas, estado
    experiments/               # CV, LSV, SWV, DPV, CA, potenciometría
    interface/
      main_window.py           # ventana principal
      plot_widget.py           # gráfico matplotlib embebido
      protocol_view.py         # terminal de protocolo
      theme.py / theme_manager.py / styles.qss   # sistema de temas
      icons/                   # iconos SVG modernos
tests/                         # pruebas unitarias
```

## Licencia

GPL-3.0 (ver `LICENSE`).