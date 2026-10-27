# Caracterización Experimental y Pruebas de Adquisición

Este directorio documenta los ensayos de caracterización eléctrica y validación del instrumento **DStat-RD** utilizando celdas de prueba con componentes pasivos de precisión (*dummy cells*).

---

## 🎯 Objetivo de los Ensayos

Demostrar cuantitativamente el rendimiento del instrumento en adquisición analógica, evaluando:
1. **Precisión frente a la Ley de Ohm** ($I = V / R$) en resistencias de 1 MΩ y 4 MΩ.
2. **Impacto crítico de la limpieza por ultrasonido con IPA:** Eliminación de restos de flux de soldadura en la PCB para suprimir corrientes de fuga parásitas (`no_clean` vs `clean`).
3. **Impacto del apantallamiento electrostático (Jaula de Faraday / Blindaje):** Supresión del acople de ruido de red electromagnético.
4. **Efecto de la calibración de ganancia del TIA:** Comparación de lectura con calibración de fábrica/por defecto vs. calibración fina.
5. **Filtro de frecuencia de red (50 Hz vs 60 Hz):** Evaluación de la reyección de línea en el conversor analógico-digital (ADC).
6. **Linealidad y rango dinámico en barridos de potencial (Linear Sweep):** Coeficiente de determinación ($R^2$) y error de fondo de escala.

---

## 📊 Resumen Comparativo Global

### 1. Cronoamperometría ($V = 100\text{ mV}$, $R_{TIA} = 3\text{ M}\Omega$)

> [!NOTE]
> **Efecto de la limpieza de flux:** En la condición sin lavar (`no_clean`), los residuos de flux en la PCB introdujeron corrientes de fuga parásitas de ~17.5 nA, provocando un desvío de **+70.92%** en la resistencia de 4 MΩ. El **lavado en batea de ultrasonido con alcohol isopropílico (IPA)** eliminó las fugas, reduciendo el error a menos del **0.7%**.

| Condición de Ensayo | $R_{\text{test}}$ | Corriente Esperada | Corriente Medida | Error Promedio | Ruido P2P | SNR (dB) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Sin lavar (con flux), Sin blindaje, Sin calib** (`no_clean_no_cal`) | 1 MΩ | 100.0 nA | 117.5 nA | **+17.50 %** | 1.91 nA | 23.3 dB |
| **Sin lavar (con flux), Sin blindaje, Sin calib** (`no_clean_no_cal`) | 4 MΩ | 25.0 nA | 42.7 nA | **+70.92 %** | 1.85 nA | 21.8 dB |
| **Lavado IPA ultrasonido + Con blindaje, Sin calib** (`clean_no_cal`) | 1 MΩ | 100.0 nA | 99.16 nA | **-0.84 %** | 0.37 nA | 27.0 dB |
| **Lavado IPA ultrasonido + Con blindaje, Sin calib** (`clean_no_cal`) | 4 MΩ | 25.0 nA | 24.83 nA | **-0.66 %** | 0.47 nA | 21.6 dB |
| **Lavado IPA ultrasonido + Con blindaje + Calibrado** (`clean_cal`) | 1 MΩ | 100.0 nA | **99.82 nA** | **-0.18 %** | **0.28 nA** | 25.5 dB |
| **Lavado IPA ultrasonido + Con blindaje + Calibrado** (`clean_cal`) | 4 MΩ | 25.0 nA | **25.11 nA** | **+0.43 %** | **0.35 nA** | 26.9 dB |
| **Lavado IPA ultrasonido + Con blindaje + Calibrado** (`clean_cal`) | Open | 0.0 nA | **0.01 nA (10 pA)** | N/A | 1.82 nA | 11.4 dB |

### 2. Barrido Lineal de Potencial (LSV / CV, $-200\text{ mV}$ a $+200\text{ mV}$)

| $R_{\text{test}}$ | $R$ Ajustada ($R_{\text{fit}}$) | Error en $R$ | Coeficiente $R^2$ | No Linealidad (% FS) | Ruido RMS | SNR (dB) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1 MΩ** (50 Hz) | **999.4 kΩ** | **-0.06 %** | **1.000000** | **0.088 %** | 38.9 pA | **74.2 dB** |
| **4 MΩ** (50 Hz) | **3.975 MΩ** | **-0.63 %** | **0.999998** | **0.265 %** | 40.0 pA | **62.0 dB** |

---

## 📑 Reportes Detallados

- **[Reporte de Cronoamperometría](./chronoamperometry.md):**  
  Análisis exhaustivo paso a paso, gráficas temporales y espectros FFT para las tres condiciones (sin blindaje, con blindaje, y con blindaje + calibración).
- **[Reporte de Barridos de Potencial (Linear Sweep)](./sweep.md):**  
  Curvas I-V, análisis de regresión por Ley de Ohm, cálculo de residuos, $R^2$ y linealidad frente al fondo de escala.

---

## 🛠️ Herramienta de Procesamiento y Análisis

Los datos crudos almacenados en la carpeta [`signals/`](./signals/) pueden ser reprocesados y analizados mediante el script ubicado en la raíz del repositorio: [`tools/analyze_signals.py`](../../tools/analyze_signals.py).

### Ejemplos de uso:

```bash
# Analizar el set calibrado y generar figuras
py -3 tools/analyze_signals.py --dir docs/characterization/signals/clean_cal

# Analizar los barridos de potencial
py -3 tools/analyze_signals.py --dir docs/characterization/signals/sweep

# Analizar recursivamente todos los ensayos
py -3 tools/analyze_signals.py --dir docs/characterization/signals -r
```
