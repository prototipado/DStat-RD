# Ensayos de Cronoamperometría con Celdas Pasivas (Dummy Cell)

Este reporte detalla los experimentos de cronoamperometría ejecutados aplicando un potencial constante de **$V = 100\text{ mV}$** utilizando una ganancia de transimpedancia $R_{TIA} = 3\text{ M}\Omega$.

---

## 🔬 Condiciones Experimentales

Se evaluaron tres configuraciones de carga conectadas entre el electrodo de trabajo (WE) y el contra/referencia (CE/RE):
1. **$R_{\text{test}} = 1\text{ M}\Omega$:** Corriente teórica esperada $I = 100\text{ mV} / 1\text{ M}\Omega = 100.0\text{ nA}$.
2. **$R_{\text{test}} = 4\text{ M}\Omega$:** Corriente teórica esperada $I = 100\text{ mV} / 4\text{ M}\Omega = 25.0\text{ nA}$.
3. **Circuito Abierto ($R_{\text{test}} = \text{Open}$):** Corriente teórica esperada $I = 0.0\text{ nA}$ (evaluación de corriente de polarización / offset de entrada).

Para cada carga, se contrastaron tres escenarios de adquisición:
- **Escenario 1:** Sin blindaje y sin calibración (`no_clean_no_cal`).
- **Escenario 2:** Con blindaje (jaula de Faraday) y sin calibración (`clean_no_cal`).
- **Escenario 3:** Con blindaje y con calibración de ganancia y offset aplicada (`clean_cal`).

---

## 📈 1. Escenario 3: Con Blindaje y Calibrado (`clean_cal`)

Este representa el modo óptimo de operación recomendado.

### Gráfica Resumen de Adquisición
![Resumen Cronoamperometría Calibrada](./signals/clean_cal/analysis/summary.png)

### Métricas Obtenidas

| Archivo | $R_{\text{test}}$ | Frecuencia ADC | Puntos | Media Medida | Esperada | Error (%) | Ruido RMS | SNR (dB) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `chrono_..._R1M_50Hz_shield` | 1 MΩ | 50 Hz | 2932 | 99.82 nA | 100.0 nA | **-0.18 %** | 35.2 pA | 25.5 dB |
| `chrono_..._R1M_60Hz_shield` | 1 MΩ | 60 Hz | 3519 | 99.82 nA | 100.0 nA | **-0.18 %** | 2.00 nA | 61.9 dB |
| `chrono_..._R4M_50Hz_shield` | 4 MΩ | 50 Hz | 2932 | 25.11 nA | 25.0 nA | **+0.43 %** | 44.8 pA | 26.9 dB |
| `chrono_..._R4M_60Hz_shield` | 4 MΩ | 60 Hz | 3519 | 25.10 nA | 25.0 nA | **+0.42 %** | 2.36 nA | 66.6 dB |
| `chrono_..._Ropen_50Hz_shield` | Open | 50 Hz | 2932 | 10.6 pA | 0.0 nA | **N/A** | 55.5 pA | 11.4 dB |
| `chrono_..._Ropen_60Hz_shield` | Open | 60 Hz | 3518 | 11.6 pA | 0.0 nA | **N/A** | 2.04 nA | 62.2 dB |

### Análisis Detallado por Resistencia (50 Hz)

#### Carga 1 MΩ (100 mV)
![1M 50Hz Calibrado](./signals/clean_cal/analysis/chrono_100mV_3Mohm_R1M_50Hz_shield_0000.png)
- Corriente media observada: **99.82 nA** frente a los 100.0 nA ideales.
- Error absoluto: **-0.18 nA** (-0.18%).
- Ruido pico a pico residual: **0.278 nA**.

#### Carga 4 MΩ (100 mV)
![4M 50Hz Calibrado](./signals/clean_cal/analysis/chrono_100mV_3Mohm_R4M_50Hz_shield_0000.png)
- Corriente media observada: **25.11 nA** frente a los 25.0 nA ideales.
- Error absoluto: **+0.11 nA** (+0.43%).
- Ruido pico a pico residual: **0.348 nA**.

#### Circuito Abierto (Open)
![Open 50Hz Calibrado](./signals/clean_cal/analysis/chrono_100mV_3Mohm_Ropen_50Hz_shield_0000.png)
- Corriente de offset residual en reposo: **~10.6 pA**.

---

## 🛡️ 2. Comparación: Efecto del Blindaje Electroestático

Comparación entre la medición sin blindaje (`no_clean_no_cal`) y con blindaje (`clean_no_cal`):

| Configuración | Carga | Sin Blindaje (Medido) | Con Blindaje (Medido) | Error Sin Blindaje | Error Con Blindaje |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **R = 1 MΩ** | 100 nA | 117.5 nA | 99.16 nA | **+17.50 %** | **-0.84 %** |
| **R = 4 MΩ** | 25 nA | 42.73 nA | 24.83 nA | **+70.92 %** | **-0.66 %** |

### Gráficas Comparativas

#### Sin Blindaje (`no_clean_no_cal`)
![Sin Blindaje](./signals/no_clean_no_cal/analysis/summary.png)
*Nótese el desplazamiento masivo de la corriente media y la introducción de corrientes de fuga parásitas inducidas por el campo eléctrico ambiente.*

#### Con Blindaje (`clean_no_cal`)
![Con Blindaje](./signals/clean_no_cal/analysis/summary.png)
*Al confinar la celda dentro de una caja metálica conectada al terminal de referencia/chasis, el error disminuye drásticamente a menos del 1%.*

---

## ⚡ 3. Efecto de la Frecuencia del Filtro ADC (50 Hz vs 60 Hz)

En regiones donde la red de distribución eléctrica es de **50 Hz** (por ejemplo, Argentina y Europa):
- Configurar el conversor a **50 Hz** activa el filtro sincrónico tipo peine (*comb filter / notch*) en los armónicos de 50 Hz.
- El ruido RMS cae de **~2 nA** (a 60 Hz) a tan solo **~35 pA** (a 50 Hz), logrando una reducción de ruido de más de un orden de magnitud.

---

## 💡 Conclusiones Operativas

1. **Uso imprescindible de blindaje:** Para cualquier experimento donde las corrientes esperadas sean inferiores a $1\ \mu\text{A}$, el uso de celda blindada (jaula de Faraday) es mandatorio.
2. **Selección de frecuencia de red:** Se debe ajustar siempre la frecuencia de rechazo en la GUI acorde a la frecuencia de red local (50 Hz o 60 Hz).
3. **Calibración:** La calibración del instrumento permite corregir las tolerancias de los resistores de retroalimentación del TIA, reduciendo el error global de lectura al orden de **±0.2% a ±0.4%**.
