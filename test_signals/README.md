# Señales de prueba (test_signals)

Capturas de cronoamperometría (CA) del DStat usadas para validar la interfaz y
el hardware.

## Formato de los archivos

Archivos de texto tabulados (`.txt`), generados por **File → Save Current Data**
de la GUI. Cada archivo:

```
# current_time
# scan 0
0.034	1.1724235e-07
0.054	1.1718275e-07
...
```

- Líneas que empiezan con `#` son metadatos (ignoradas por el analizador).
- Columna 1: tiempo (s). Columna 2: corriente (A).
- Separador: tabulación.

## Convención de nombres

`chrono_{potencial}mV_{ganancia}Mohm_R{R}{unidad}_{frecuencia}Hz_{blindaje}_{id}.txt`

Ejemplo: `chrono_100mV_3Mohm_R1M_50Hz_no_shield_0000.txt`

- `100mV` — potencial aplicado (mV)
- `3Mohm` — resistor de ganancia del TIA (3 MΩ)
- `R1M` — resistor de prueba (1 MΩ)
- `50Hz` — frecuencia de muestreo del ADC
- `no_shield` — condición de blindaje
- `0000` — índice de captura

## Análisis

```powershell
cd D:\PROYECTOS_SIN_REPOS\Potensiostato\DStat-GUI-dev2.0
python tools/analyze_signals.py
```

Genera `test_signals/analysis/summary.csv` y figuras PNG (serie temporal + FFT por
captura y un resumen comparativo contra la expectativa de Ohm).

Opciones:
- `--dir <carpeta>` — directorio de capturas (default `test_signals`)
- `--out <carpeta>` — directorio de salida (default `<dir>/analysis`)
- `--no-plot` — solo estadísticas, sin figuras
- `--pattern "*.txt"` — patrón glob de archivos
