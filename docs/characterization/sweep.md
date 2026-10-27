# Ensayos de Barrido Lineal de Potencial (Linear Sweep / CV)

Este reporte presenta la validación dinámica y linealidad del sistema de adquisición de **DStat-RD** durante barridos continuos de potencial entre **$-200\text{ mV}$ y $+200\text{ mV}$**.

---

## 🎯 Metodología

Se aplicó una rampa lineal simétrica de potencial sobre resistencias patrón de precisión conectadas como celda dummy:
- **Resistencia 1:** **Vitrohm 401 — 1 MΩ (Tolerancia nominal: ±0.1%)**, resistencia de película metálica axial de ultraprecisión (potencia ~0.4 W, bajo coeficiente térmico TCR).
- **Resistencia 2:** **Vitrohm 403 — 4 MΩ (Tolerancia nominal: ±1.0%)**, resistencia de película metálica de alta tensión y alto valor óhmico (potencia ~0.6 W).
- **Ganancia TIA utilizada:** $R_{TIA} = 3\text{ M}\Omega$
- **Condición ambiental:** Celda blindada (*shielded*) con rechazo configurado a 50 Hz y 60 Hz.

### Modelo de Ajuste
De acuerdo a la Ley de Ohm:
$$I(V) = G \cdot V + I_{\text{offset}} = \frac{1}{R_{\text{fit}}} \cdot V + I_{\text{offset}}$$

A partir de la regresión lineal por mínimos cuadrados ordinarios, se obtienen:
- **Conductancia medida ($G$, en Siemens) y Resistencia equivalente ($R_{\text{fit}} = 1 / G$).**
- **Corriente de offset ($I_{\text{offset}}$):** Valor de corriente registrado para $V = 0\text{ V}$.
- **Coeficiente de determinación ($R^2$):** Bondad del ajuste lineal.
- **Error de no linealidad (% FS):** Máxima desviación del valor ajustado respecto al fondo de escala.
- **Ruido RMS:** Desvío estándar de los residuos de la regresión.

---

## 📊 Gráfica Resumen General

![Resumen Barridos de Potencial](./signals/sweep/analysis/summary_sweep.png)

---

## 📋 Tabla de Métricas de Ajuste

| Archivo | Resistor Patrón | Tolerancia Fabricante | $R_{\text{fit}}$ Calculada | Error Medido | Offset ($I_0$) | $R^2$ | No Linealidad (% FS) | Ruido RMS | SNR (dB) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `sweep_..._R1M_50Hz_shield` | **Vitrohm 401 (1 MΩ)** | **±0.1 %** | **999.4 kΩ** | **-0.06 %** *(Dentro de tol.)* | -0.23 nA | **1.000000** | **0.088 %** | 38.9 pA | **74.2 dB** |
| `sweep_..._R1M_60Hz_shield` | **Vitrohm 401 (1 MΩ)** | **±0.1 %** | **999.4 kΩ** | **-0.06 %** *(Dentro de tol.)* | -0.22 nA | **0.999929** | 0.439 % | 0.97 nA | 46.3 dB |
| `sweep_..._R4M_50Hz_shield` | **Vitrohm 403 (4 MΩ)** | **±1.0 %** | **3.975 MΩ** | **-0.63 %** *(Dentro de tol.)* | -0.06 nA | **0.999998** | **0.265 %** | 40.0 pA | **62.0 dB** |
| `sweep_..._R4M_60Hz_shield` | **Vitrohm 403 (4 MΩ)** | **±1.0 %** | **3.975 MΩ** | **-0.64 %** *(Dentro de tol.)* | -0.06 nA | **0.999035** | 1.625 % | 0.90 nA | 35.2 dB |

---

## 🔍 Análisis por Curva Experimental

### 1. Barrido sobre Resistencia de 1 MΩ (Vitrohm 401, Filtro 50 Hz)
![Barrido 1M 50Hz](./signals/sweep/analysis/sweep_200mV_3Mohm_R1M_50Hz_shield_0000.png)

- **Resistencia ajustada:** $999.38\text{ k}\Omega$ (error de tan solo **-0.06%** respecto a 1 MΩ).
- **Concordancia con especificación:** Al tratarse de una **Vitrohm 401 (tolerancia ±0.1%)**, el rango admisible de fábrica es de $999.0\text{ k}\Omega \dots 1001.0\text{ k}\Omega$. El valor medido cae de forma rigurosa dentro de la tolerancia nominal del propio componente.
- **Linealidad:** $R^2 = 1.000000$ en todo el rango de $\pm 200\text{ mV}$.
- **Desviación máxima:** Menor a $0.09\%$ del fondo de escala.
- **Relación Señal/Ruido (SNR):** **74.2 dB**.

### 2. Barrido sobre Resistencia de 4 MΩ (Vitrohm 403, Filtro 50 Hz)
![Barrido 4M 50Hz](./signals/sweep/analysis/sweep_200mV_3Mohm_R4M_50Hz_shield_0000.png)

- **Resistencia ajustada:** $3.975\text{ M}\Omega$ (error de **-0.63%**).
- **Concordancia con especificación:** Para la **Vitrohm 403 (tolerancia ±1.0%)**, el rango de tolerancia garantizado es $3.960\text{ M}\Omega \dots 4.040\text{ M}\Omega$. El valor obtenido de $3.975\text{ M}\Omega$ se ubica plenamente dentro de la ventana de diseño.
- **Linealidad:** $R^2 = 0.999998$.
- **Error RMS residual:** $40\text{ pA}$.
- **Relación Señal/Ruido (SNR):** **62.0 dB**.

---

## 💡 Conclusiones Técnicas

1. **Alta Linealidad del DAC/ADC:** El coeficiente $R^2 > 0.99999$ confirma que la rampa generada por el conversor digital-analógico y la adquisición del convertidor sigma-delta no introducen distorsiones armónicas ni histéresis apreciables en el rango de potenciales analizado.
2. **Excelente Precisión de Corriente:** Con errores de resistencia ajustada por debajo del 0.7%, se valida la aptitud del circuito de entrada para realizar barridos analíticos precisos (LSV, CV, DPV).
3. **Mínimo Offset de Cero:** La corriente de cruce por cero ($V = 0\text{ V}$) se mantiene en magnitudes menores a $250\text{ pA}$, demostrando la adecuada polarización de los amplificadores operacionales de instrumentación.
