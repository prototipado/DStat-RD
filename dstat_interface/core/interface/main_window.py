"""Main application window.

Replaces the GTK Glade-based `Main` class from the original with a pure
PyQt6 implementation that exposes the same logical sections described in the
README:

1. Menu bar
2. ADC settings
3. Potentiostat gain
4. Experiment panel
5. Experiment control (Execute / Stop)
6. Communications panel (port, connect, OCP)
7. Data display tabs (Plot | Raw Data | Info)
8. Autosave controls
"""

import os
import time
import logging
import multiprocessing
from datetime import datetime
from collections import OrderedDict

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QGroupBox, QLabel, QComboBox, QPushButton, QCheckBox, QLineEdit,
    QFileDialog, QProgressBar, QStatusBar, QTabWidget, QMessageBox,
    QSplitter, QSizePolicy, QFrame, QScrollArea, QApplication,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QAction

from ..dstat import state, comm, boards
from ..errors import InputError
from ..experiments import idle
from ..experiments.experiment_loops import BaseLoop
from ..analysis import AnalysisOptionsDialog, do_analysis
from .. import validation
from .exp_panel import ExperimentsPanel
from .plot_widget import PlotWidget
from .data_view import DataView, InfoView
from .protocol_view import ProtocolView
from . import save_dialog

try:
    import zmq
    _ZMQ_AVAILABLE = True
except ImportError:
    _ZMQ_AVAILABLE = False

logger = logging.getLogger(__name__)

VERSION = "2.1.0"

# ADC sample rate options: (display label, command value)
# Values are hexadecimal ADS1255 DRATE codes parsed with %hhx by the firmware.
ADC_RATES = [
    ("2.5 Hz",  "03"),
    ("5 Hz",    "13"),
    ("10 Hz",   "23"),
    ("15 Hz",   "33"),
    ("25 Hz",   "43"),
    ("30 Hz",   "53"),
    ("50 Hz",   "63"),
    ("60 Hz",   "72"),
    ("100 Hz",  "82"),
    ("500 Hz",  "92"),
    ("1 kHz",   "A1"),
    ("2 kHz",   "B0"),
    ("3.75 kHz", "C0"),
    ("7.5 kHz", "D0"),
    ("15 kHz",  "E0"),
    ("30 kHz",  "F0"),
]

# ADC PGA options: (label, command value) - ADS_PGA_* in ads1255.h
ADC_PGA = [
    ("1x",  "0"),
    ("2x",  "1"),
    ("4x",  "2"),
    ("8x",  "3"),
    ("16x", "4"),
    ("32x", "5"),
    ("64x", "6"),
]

# ---------------------------------------------------------------------------
# Experiment Guide HTML
# ---------------------------------------------------------------------------

_EXPERIMENT_GUIDE_HTML = """
<html><head><style>
  body  { font-family: Segoe UI, Arial, sans-serif; font-size: 10pt; margin: 12px; }
  h1    { font-size: 13pt; color: #1a4f8a; border-bottom: 1px solid #aac; padding-bottom: 4px; }
  h2    { font-size: 11pt; color: #1a4f8a; margin-top: 18px; margin-bottom: 2px; }
  h3    { font-size: 10pt; color: #444; margin-top: 10px; margin-bottom: 2px; }
  table { border-collapse: collapse; width: 100%; margin-top: 6px; }
  th    { background: #dde8f5; text-align: left; padding: 4px 8px; }
  td    { padding: 3px 8px; vertical-align: top; }
  tr:nth-child(even) td { background: #f4f7fc; }
  .tag  { color: #888; font-style: italic; font-size: 9pt; }
  ul    { margin: 4px 0 4px 18px; }
</style></head><body>

<h1>Guía de Modos de Experimento</h1>

<!-- ═══════════════════════════════════════════════════════════════════ -->
<h2>1. Cyclic Voltammetry (CV) — Voltametría Cíclica</h2>
<p class="tag">Resultado: gráfico Corriente vs. Tensión (ciclos)</p>
<p>
  Barre el potencial desde un valor de inicio hasta un vértice, luego regresa
  (y opcionalmente repite varios ciclos). Es la técnica más empleada para
  <b>caracterizar reacciones redox</b>, determinar potenciales de oxidación y
  reducción, y estudiar la reversibilidad de un proceso electroquímico.
</p>
<h3>Parámetros principales</h3>
<table>
  <tr><th>Parámetro</th><th>Descripción</th><th>Valor típico</th></tr>
  <tr><td>Start (mV)</td><td>Potencial inicial del barrido</td><td>0</td></tr>
  <tr><td>Vertex 1 (mV)</td><td>Potencial máximo del barrido</td><td>+500</td></tr>
  <tr><td>Vertex 2 (mV)</td><td>Potencial mínimo del barrido</td><td>−500</td></tr>
  <tr><td>Slope (mV/s)</td><td>Velocidad de barrido (scan rate)</td><td>100</td></tr>
  <tr><td>Scans</td><td>Número de ciclos completos</td><td>1–5</td></tr>
</table>
<h3>Usos habituales</h3>
<ul>
  <li>Caracterización de electrocatalizadores y materiales de electrodo</li>
  <li>Estudio de mecanismos de reacción redox (reversible / irreversible)</li>
  <li>Determinación de coeficientes de difusión (ecuación de Randles-Ševčík)</li>
  <li>Diagnóstico rápido del estado del electrodo y del analito</li>
</ul>

<!-- ═══════════════════════════════════════════════════════════════════ -->
<h2>2. Linear Sweep Voltammetry (LSV) — Voltametría de Barrido Lineal</h2>
<p class="tag">Resultado: gráfico Corriente vs. Tensión (barrido único)</p>
<p>
  Variante simplificada de CV: barre el potencial en una sola dirección de
  <i>Start</i> a <i>Stop</i>. Genera una curva de polarización que muestra
  la corriente en función del potencial.
</p>
<h3>Parámetros principales</h3>
<table>
  <tr><th>Parámetro</th><th>Descripción</th><th>Valor típico</th></tr>
  <tr><td>Start (mV)</td><td>Potencial inicial</td><td>−200</td></tr>
  <tr><td>Stop (mV)</td><td>Potencial final</td><td>+200</td></tr>
  <tr><td>Slope (mV/s)</td><td>Velocidad de barrido</td><td>100</td></tr>
</table>
<h3>Usos habituales</h3>
<ul>
  <li>Curvas de polarización de pilas de combustible y electrolizadores</li>
  <li>Determinación de la corriente límite de difusión</li>
  <li>Análisis de corrosión y potencial de picado</li>
  <li>Screening rápido de materiales (basta un solo barrido)</li>
</ul>

<!-- ═══════════════════════════════════════════════════════════════════ -->
<h2>3. Square Wave Voltammetry (SWV) — Voltametría de Onda Cuadrada</h2>
<p class="tag">Resultado: corriente neta, directa e inversa vs. Tensión</p>
<p>
  Superpone una señal de onda cuadrada al barrido lineal y registra la
  diferencia de corriente entre los pulsos directos e inversos. Suprime
  prácticamente toda la corriente capacitiva, logrando
  <b>límites de detección muy bajos</b>.
</p>
<h3>Parámetros principales</h3>
<table>
  <tr><th>Parámetro</th><th>Descripción</th><th>Valor típico</th></tr>
  <tr><td>Start / Stop (mV)</td><td>Rango de potencial del barrido</td><td>0 / +500</td></tr>
  <tr><td>Step (mV)</td><td>Incremento de potencial por ciclo</td><td>2</td></tr>
  <tr><td>Pulse (mV)</td><td>Amplitud de la onda cuadrada</td><td>25</td></tr>
  <tr><td>Frequency (Hz)</td><td>Frecuencia de la onda cuadrada</td><td>25</td></tr>
  <tr><td>Scans</td><td>Número de repeticiones</td><td>1</td></tr>
</table>
<h3>Usos habituales</h3>
<ul>
  <li>Detección de trazas de metales pesados (plomo, cadmio, mercurio)</li>
  <li>Análisis de fármacos y biomarcadores a bajas concentraciones</li>
  <li>Sensores electroquímicos de alta sensibilidad</li>
  <li>Mediciones rápidas donde SN es crítico</li>
</ul>

<!-- ═══════════════════════════════════════════════════════════════════ -->
<h2>4. Differential Pulse Voltammetry (DPV) — Voltametría de Pulso Diferencial</h2>
<p class="tag">Resultado: corriente diferencial vs. Tensión</p>
<p>
  Aplica pulsos rectangulares de amplitud fija alternando entre dos potenciales
  y registra la <b>diferencia de corriente</b> medida al final de cada pulso. La
  corriente diferencial cancelsa buena parte de la corriente capacitiva, por lo
  que mejora la resolución frente a LSV.
</p>
<h3>Parámetros principales</h3>
<table>
  <tr><th>Parámetro</th><th>Descripción</th><th>Valor típico</th></tr>
  <tr><td>Start / Stop (mV)</td><td>Rango de potencial del barrido</td><td>0 / +500</td></tr>
  <tr><td>Step (mV)</td><td>Incremento de potencial</td><td>2–5</td></tr>
  <tr><td>Pulse (mV)</td><td>Amplitud del pulso</td><td>25–50</td></tr>
  <tr><td>Period (ms)</td><td>Periodo entre pulsos</td><td>200–500</td></tr>
  <tr><td>Width (ms)</td><td>Duración del pulso (<b>menor</b> que el periodo)</td><td>20–50</td></tr>
</table>
<p>El ADC muestrea 1/(frecuencia de muestreo) antes del final del pulso, así que
la frecuencia de muestreo debe ser mucho mayor que el ancho de pulso para reducir
la corriente capacitiva.</p>
<h3>Usos habituales</h3>
<ul>
  <li>Análisis de trazas en agua, suelos y bebidas</li>
  <li>Determinación de metales pesados con elevada selectividad</li>
  <li>Medición de fármacos en fluidos biológicos</li>
</ul>

<!-- ═══════════════════════════════════════════════════════════════════ -->
<h2>5. Chronoamperometry (CA) — Cronoamperometría</h2>
<p class="tag">Resultado: gráfico Corriente vs. Tiempo</p>
<p>
  Aplica uno o varios escalones de potencial y registra cómo evoluciona la
  corriente en el tiempo. Permite caracterizar procesos controlados por
  difusión y cinética de transferencia de carga.
</p>
<h3>Parámetros principales</h3>
<table>
  <tr><th>Parámetro</th><th>Descripción</th><th>Valor típico</th></tr>
  <tr><td>Potential (mV)</td><td>Potencial aplicado en cada escalón</td><td>depende del sistema</td></tr>
  <tr><td>Time (s)</td><td>Duración de cada escalón</td><td>10–60</td></tr>
</table>
<p>Se pueden encadenar múltiples pares potencial/tiempo con los botones
<b>+ Add</b> y <b>− Remove</b>.</p>
<h3>Usos habituales</h3>
<ul>
  <li>Cálculo de coeficientes de difusión (ecuación de Cottrell)</li>
  <li>Análisis de biosensores amperométricos (glucosa, H₂O₂)</li>
  <li>Estudio de adsorción y nucleación en electrodepositación</li>
  <li>Evaluación de la respuesta en el tiempo de un sensor</li>
</ul>

<!-- ═══════════════════════════════════════════════════════════════════ -->
<h2>6. Potentiometry — Potenciometría</h2>
<p class="tag">Resultado: gráfico Tensión vs. Tiempo</p>
<p>
  Mide el potencial de circuito abierto (OCP) entre el electrodo de trabajo y
  el de referencia durante un tiempo determinado, sin aplicar corriente.
  Ideal para electrodos selectivos de iones y mediciones de pH.
</p>
<h3>Parámetros principales</h3>
<table>
  <tr><th>Parámetro</th><th>Descripción</th><th>Valor típico</th></tr>
  <tr><td>Time (s)</td><td>Duración total de la medición</td><td>60</td></tr>
</table>
<h3>Usos habituales</h3>
<ul>
  <li>Medición de pH con electrodo de vidrio</li>
  <li>Electrodos selectivos de iones (ISE): Na⁺, K⁺, Cl⁻, etc.</li>
  <li>Monitoreo de estabilidad del potencial antes de un experimento</li>
  <li>Titulaciones potenciométricas</li>
</ul>

<!-- ═══════════════════════════════════════════════════════════════════ -->
<h2>Preconditioning — Preacondicionamiento</h2>
<p>
  Disponible en CV, LSV y SWV. Se ejecuta automáticamente <b>antes</b> del
  experimento principal y tiene dos etapas opcionales:
</p>
<table>
  <tr><th>Etapa</th><th>Parámetros</th><th>Propósito</th></tr>
  <tr>
    <td><b>Cleaning</b></td>
    <td>Potential (mV) + Time (s)</td>
    <td>Aplica un potencial para limpiar (oxidar/reducir) la superficie
        del electrodo antes de la medición.</td>
  </tr>
  <tr>
    <td><b>Deposition</b></td>
    <td>Potential (mV) + Time (s)</td>
    <td>Deposita el analito sobre el electrodo (preconcentración).
        Fundamental en análisis de trazas con SWV.</td>
  </tr>
</table>
<p>Dejar ambos campos en 0 deshabilita el preacondicionamiento.</p>

<h2>OCP — Potencial de Circuito Abierto</h2>
<p>
  Mientras no se ejecuta ningún experimento, el campo <b>OCP</b> del panel de
  comunicaciones muestra de forma continua el potencial de circuito abierto.
  Se detiene automáticamente al lanzar un experimento y se reanuda al terminar.
</p>
<p>Requiere firmware <b>v1.2 o superior</b>; en placas v1.1 el campo muestra
<b>n/a</b>.</p>

<h2>Límites del hardware</h2>
<p>Los parámetros se validan antes de cada ejecución:</p>
<table>
  <tr><th>Parámetro</th><th>Rango admitido</th></tr>
  <tr><td>Potenciales (Start, Stop, vértices, preacondicionamiento)</td><td>−1500 … 1499 mV</td></tr>
  <tr><td>Slope (mV/s)</td><td>1 … 2000</td></tr>
  <tr><td>Step (mV)</td><td>1 … 200</td></tr>
  <tr><td>Pulse (mV)</td><td>1 … 150</td></tr>
  <tr><td>Frequency (Hz)</td><td>1 … 1000</td></tr>
  <tr><td>Period / Width (ms)</td><td>1 … 1000, y Width &lt; Period</td></tr>
  <tr><td>Scans</td><td>1 … 255</td></tr>
  <tr><td>Tiempos (s)</td><td>0 … 65535 (contador de 16 bits)</td></tr>
</table>

</body></html>
"""


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"DStat GUI 2.1  v{VERSION}")
        self.resize(1200, 800)
        self.setMinimumSize(960, 640)

        self.current_exp = None
        self.current_loop = None
        self._ocp_timer = QTimer(self)
        self._ocp_timer.setInterval(500)
        self._ocp_timer.timeout.connect(self._poll_ocp)
        self._ocp_running = False
        self._autosave_counter: dict = {}

        self._analysis_dialog = AnalysisOptionsDialog(self)
        self._dropbot_connected = False

        self._build_menu()
        self._build_central()
        self._build_statusbar()

        # Poll the serial subprocess for protocol traffic.
        self._trace_timer = QTimer(self)
        self._trace_timer.setInterval(100)
        self._trace_timer.timeout.connect(self._poll_trace)
        self._trace_timer.start()

        # Populate serial ports
        self._refresh_ports()

        # Pre-populate gain combo with BaseBoard defaults so it is never empty
        state.board_instance = boards.BaseBoard()
        self._populate_gain_combo()

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------

    def _build_menu(self):
        bar = self.menuBar()

        # File
        file_menu = bar.addMenu("&File")

        act_save_data = QAction("Save Current Data…", self)
        act_save_data.triggered.connect(self._on_save_data)
        file_menu.addAction(act_save_data)

        act_save_plot = QAction("Save Plot…", self)
        act_save_plot.triggered.connect(self._on_save_plot)
        file_menu.addAction(act_save_plot)

        file_menu.addSeparator()

        act_save_params = QAction("Save Parameters…", self)
        act_save_params.triggered.connect(self._on_save_params)
        file_menu.addAction(act_save_params)

        act_load_params = QAction("Load Parameters…", self)
        act_load_params.triggered.connect(self._on_load_params)
        file_menu.addAction(act_load_params)

        file_menu.addSeparator()

        act_quit = QAction("&Quit", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # Dropbot
        dropbot_menu = bar.addMenu("&Dropbot")
        self._act_dropbot_connect = QAction("Connect", self)
        self._act_dropbot_connect.setToolTip("Listen for µDrop connection over ZMQ")
        self._act_dropbot_connect.triggered.connect(self._on_dropbot_connect)
        if not _ZMQ_AVAILABLE:
            self._act_dropbot_connect.setEnabled(False)
            self._act_dropbot_connect.setText("Connect  (zmq not installed)")
        dropbot_menu.addAction(self._act_dropbot_connect)

        self._act_dropbot_disconnect = QAction("Disconnect", self)
        self._act_dropbot_disconnect.setEnabled(False)
        self._act_dropbot_disconnect.triggered.connect(self._on_dropbot_disconnect)
        dropbot_menu.addAction(self._act_dropbot_disconnect)

        # Analysis
        analysis_menu = bar.addMenu("&Analysis")
        act_analysis_opts = QAction("Analysis Options…", self)
        act_analysis_opts.triggered.connect(self._on_analysis_options)
        analysis_menu.addAction(act_analysis_opts)

        act_run_analysis = QAction("Run Analysis", self)
        act_run_analysis.triggered.connect(self._on_run_analysis)
        analysis_menu.addAction(act_run_analysis)

        # View
        view_menu = bar.addMenu("&View")
        self._act_protocol = QAction("Protocol Terminal", self)
        self._act_protocol.setCheckable(True)
        self._act_protocol.setChecked(True)
        self._act_protocol.setShortcut("Ctrl+P")
        self._act_protocol.setToolTip(
            "Show the raw serial conversation with the DStat"
        )
        self._act_protocol.triggered.connect(self._toggle_protocol_panel)
        view_menu.addAction(self._act_protocol)

        view_menu.addSeparator()

        # Theme submenu
        theme_menu = view_menu.addMenu("Theme")
        from .theme_manager import load_preference, save_preference, apply_theme
        self._theme_actions = {}
        for mode, label in (("system", "System (default)"), ("light", "Light"), ("dark", "Dark")):
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(load_preference() == mode)
            act.triggered.connect(lambda checked=False, m=mode: self._on_theme_change(m))
            theme_menu.addAction(act)
            self._theme_actions[mode] = act

        # Help
        help_menu = bar.addMenu("&Help")
        act_guide = QAction("Experiment Guide", self)
        act_guide.triggered.connect(self._on_experiment_guide)
        help_menu.addAction(act_guide)
        help_menu.addSeparator()
        act_about = QAction("About", self)
        act_about.triggered.connect(self._on_about)
        help_menu.addAction(act_about)

    # ------------------------------------------------------------------
    # Central widget layout
    # ------------------------------------------------------------------

    def _build_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 4, 6, 4)
        root.setSpacing(4)

        # Keep the original GTK layout: experiment controls on the left,
        # data notebook in the middle, the protocol terminal on the right,
        # and serial controls along the bottom.
        left_contents = QWidget()
        left_layout = QVBoxLayout(left_contents)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(6)

        left_layout.addWidget(self._build_adc_group())
        left_layout.addWidget(self._build_gain_group())
        left_layout.addWidget(self._build_exp_group())
        left_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(left_contents)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(270)
        scroll.setMaximumWidth(380)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Execute/Stop fixed at the bottom of the left column (outside scroll).
        self._control_bar = self._build_control_group()

        right_contents = QWidget()
        right_layout = QVBoxLayout(right_contents)
        right_layout.setContentsMargins(2, 4, 2, 4)
        right_layout.setSpacing(4)
        right_layout.addWidget(self._build_autosave_group())

        self.tabs = QTabWidget()
        self.plot_widget = PlotWidget()
        self.data_view = DataView()
        self.info_view = InfoView()

        self.tabs.addTab(self.plot_widget, "Plot")
        self.tabs.addTab(self.data_view, "Raw Data")
        self.tabs.addTab(self.info_view,  "Info")
        right_layout.addWidget(self.tabs, 1)

        left_column = QWidget()
        left_column_layout = QVBoxLayout(left_column)
        left_column_layout.setContentsMargins(0, 0, 0, 0)
        left_column_layout.setSpacing(4)
        left_column_layout.addWidget(scroll, 1)
        left_column_layout.addWidget(self._control_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_column)
        splitter.addWidget(right_contents)

        # Protocol terminal on the right-hand side.  It is part of the main
        # splitter so the user can resize or collapse it while reviewing the
        # serial conversation.
        self.protocol_view = ProtocolView()
        self.protocol_view.setMinimumWidth(260)
        splitter.addWidget(self.protocol_view)

        splitter.setSizes([300, 560, 340])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        root.addWidget(splitter, 1)

        root.addWidget(self._build_comm_group())

    def _build_adc_group(self) -> QGroupBox:
        grp = QGroupBox("ADC Settings")
        form = QFormLayout(grp)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.adc_pga_combo = QComboBox()
        for label, _ in ADC_PGA:
            self.adc_pga_combo.addItem(label)
        self.adc_pga_combo.setCurrentIndex(1)  # default 2x
        form.addRow("PGA:", self.adc_pga_combo)

        self.adc_rate_combo = QComboBox()
        for label, _ in ADC_RATES:
            self.adc_rate_combo.addItem(label)
        self.adc_rate_combo.setCurrentIndex(7)  # default 60 Hz
        form.addRow("Sample Rate:", self.adc_rate_combo)

        self.buffer_check = QCheckBox("Enabled")
        self.buffer_check.setChecked(True)
        self.buffer_check.setToolTip(
            "The ADC's input buffer greatly increases input impedance. "
            "Should generally be enabled."
        )
        form.addRow("Input Buffer:", self.buffer_check)

        self.short_check = QCheckBox("Enabled")
        self.short_check.setChecked(False)
        self.short_check.setToolTip("Short CE and RE terminals together.")
        form.addRow("2 Electrode Mode:", self.short_check)

        return grp

    def _build_gain_group(self) -> QGroupBox:
        grp = QGroupBox("Potentiostat Settings")
        form = QFormLayout(grp)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.gain_combo = QComboBox()
        form.addRow("Gain:", self.gain_combo)
        return grp

    def _build_exp_group(self) -> QGroupBox:
        grp = QGroupBox("Experiment")
        layout = QVBoxLayout(grp)
        self.exp_panel = ExperimentsPanel()
        layout.addWidget(self.exp_panel)
        return grp

    def _build_control_group(self) -> QGroupBox:
        grp = QGroupBox("Experiment Control")
        outer = QVBoxLayout(grp)
        hbox = QHBoxLayout()

        self.btn_execute = QPushButton("Execute")
        self.btn_execute.setObjectName("btn_execute")
        self.btn_execute.setEnabled(False)
        self.btn_execute.clicked.connect(self._on_execute)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        hbox.addWidget(self.btn_execute)
        hbox.addWidget(self.btn_stop)

        outer.addLayout(hbox)
        outer.addWidget(self.progress_bar)
        return grp

    def _build_comm_group(self) -> QGroupBox:
        grp = QGroupBox("Communications")
        grid = QGridLayout(grp)
        grid.setContentsMargins(8, 4, 8, 4)
        grid.setVerticalSpacing(4)
        grid.setHorizontalSpacing(6)

        grid.addWidget(QLabel("Serial Port:"), 0, 0)
        self.port_combo = QComboBox()
        self.port_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid.addWidget(self.port_combo, 0, 1)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self._refresh_ports)
        grid.addWidget(self.btn_refresh, 0, 2)

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("btn_connect")
        self.btn_connect.clicked.connect(self._on_connect)
        grid.addWidget(self.btn_connect, 0, 3)

        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setObjectName("btn_disconnect")
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.clicked.connect(self._on_disconnect)
        grid.addWidget(self.btn_disconnect, 0, 4)

        grid.addWidget(QLabel("OCP (V):"), 1, 0)
        self.ocp_label = QLabel("---")
        self.ocp_label.setFrameShape(QFrame.Shape.StyledPanel)
        grid.addWidget(self.ocp_label, 1, 1, 1, 4)

        return grp

    def _build_autosave_group(self) -> QGroupBox:
        grp = QGroupBox("Autosave")
        layout = QHBoxLayout(grp)
        layout.setContentsMargins(8, 4, 8, 4)

        self.autosave_check = QCheckBox("Enable autosave")
        layout.addWidget(self.autosave_check)

        layout.addWidget(QLabel("Folder:"))
        self.autosave_dir = QLineEdit()
        self.autosave_dir.setPlaceholderText("Save directory…")
        layout.addWidget(self.autosave_dir, 1)

        btn_browse = QPushButton("…")
        btn_browse.setMinimumWidth(36)
        btn_browse.setToolTip("Browse folder")
        btn_browse.clicked.connect(self._browse_autosave_dir)
        layout.addWidget(btn_browse)

        layout.addWidget(QLabel("Filename:"))
        self.autosave_name = QLineEdit("experiment")
        self.autosave_name.setMaximumWidth(180)
        layout.addWidget(self.autosave_name)

        return grp

    def _build_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Not connected.")

    # ------------------------------------------------------------------
    # Port / connection helpers
    # ------------------------------------------------------------------

    def _refresh_ports(self):
        devices = comm.SerialDevices()
        self.port_combo.clear()
        for p in devices.ports:
            self.port_combo.addItem(p)

    def _populate_gain_combo(self):
        """Fill gain combo from the connected board's gain labels."""
        self.gain_combo.clear()
        if state.board_instance is None:
            return
        for idx, label in enumerate(state.board_instance.gain_labels):
            if label is not None:
                self.gain_combo.addItem(label, idx)
        default = state.board_instance.gain_default_index
        self.gain_combo.setCurrentIndex(default)

    # ------------------------------------------------------------------
    # Connect / disconnect
    # ------------------------------------------------------------------

    @pyqtSlot()
    def _on_connect(self):
        port = self.port_combo.currentText()
        if not port:
            self._show_status("No serial port selected.")
            return

        self._show_status(f"Connecting to {port}…")
        self.protocol_view.append(
            "info", f"--- connecting to {port} ---"
        )
        try:
            state.ser = comm.SerialConnection()
            state.ser.connected.connect(self._on_serial_connected)
            state.ser.disconnected.connect(self._on_serial_disconnected)
            state.ser.connect_serial(port)
        except comm.ConnectionError as e:
            self._show_status(f"Connection failed: {e}")
            self.protocol_view.append("error", f"connection failed: {e}")
            if state.ser is not None:
                self._poll_trace()
            state.ser = None

    @pyqtSlot()
    def _on_serial_connected(self):
        # Identify the board, then read its EEPROM settings so that the
        # gain trims are available when experiments are constructed.
        try:
            if not comm.version_check():
                detail = state.ser.last_error if state.ser else None
                self._connection_failed(
                    f"Communication error: {detail or 'no version reply from DStat.'}"
                )
                return

            if state.dstat_version is not None:
                state.board_instance = boards.get_board(str(state.dstat_version))
            else:
                logger.warning("Unknown firmware version; assuming generic board.")
                state.board_instance = boards.BaseBoard()

            comm.read_settings()
        except comm.ConnectionError as e:
            self._connection_failed(f"Communication error: {e}")
            return

        self._populate_gain_combo()

        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)
        self.btn_execute.setEnabled(True)

        board = state.board_instance
        version_text = str(state.dstat_version) if state.dstat_version else "unknown"
        self.protocol_view.append(
            "info", f"board {board.pcb_version}, firmware {version_text}"
        )
        self._show_status(f"Connected. Board: {board.pcb_version} (firmware {version_text})")
        self.info_view.append(
            f"Connected. Board: {board.pcb_version}, firmware: {version_text}"
        )

        # Start OCP polling
        self._start_ocp()

    def _connection_failed(self, message: str):
        self.info_view.append(f"ERROR: {message}")
        if state.ser and state.ser.is_connected:
            state.ser.disconnect_serial()
        self._poll_trace()
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.btn_execute.setEnabled(False)
        self._show_status(message)

    @pyqtSlot()
    def _on_serial_disconnected(self):
        self._ocp_timer.stop()
        self._ocp_running = False
        if self.current_loop:
            self.current_loop._stop_timers()
        # Flush anything the worker queued before it stopped, then close the
        # protocol log section with a visible separator.
        self._poll_trace()
        self.protocol_view.append("info", "--- disconnected ---")
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.btn_execute.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.ocp_label.setText("---")
        self._show_status("Disconnected.")
        state.reset()

    @pyqtSlot()
    def _on_disconnect(self):
        self._ocp_timer.stop()
        if self.current_loop:
            self.current_loop._stop_timers()
        if state.ser and state.ser.is_connected:
            self._stop_ocp()
            state.ser.disconnect_serial()

    # ------------------------------------------------------------------
    # OCP polling
    # ------------------------------------------------------------------

    def _start_ocp(self):
        """Start the continuous open-circuit-potential readout."""
        if state.ser is None or not state.ser.is_connected:
            return
        if not comm.supports_ocp():
            self.ocp_label.setText("n/a")
            self.ocp_label.setToolTip(
                "OCP / potentiometry requires DStat firmware v1.2 or newer."
            )
            logger.info("OCP not supported by this board.")
            return

        try:
            state.ser.flush_data()
            state.ser.flush_proc()
            state.ser.start_exp(idle.OCPExp())
        except (comm.ConnectionError, EOFError, OSError) as exc:
            logger.exception("Could not resume OCP readout")
            message = f"Experiment finished, but OCP readout could not resume: {exc}"
            self.info_view.append(f"COMMUNICATION ERROR: {message}")
            self._show_status(message)
            if state.ser and state.ser.is_connected:
                state.ser.disconnect_serial()
            return

        self._ocp_running = True
        self._ocp_timer.start()

    def _stop_ocp(self):
        """Abort the OCP readout and wait for the subprocess to finish."""
        self._ocp_timer.stop()

        if not self._ocp_running:
            return state.ser is not None and state.ser.is_connected

        try:
            state.ser.send_ctrl("a")
            # Drain the return code so it is not mistaken for an experiment result.
            for _ in range(50):
                status = state.ser.get_proc()
                if status in ("DONE", "ABORT"):
                    break
                if status in ("SERIAL_ERROR", "DISCONNECT"):
                    raise comm.ConnectionError(
                        f"Serial worker stopped while ending OCP ({status})."
                    )
                QApplication.processEvents()
                time.sleep(0.05)

            state.ser.flush_data()
            state.ser.flush_proc()
        except (comm.ConnectionError, EOFError, OSError, ValueError) as exc:
            logger.exception("Could not stop OCP cleanly")
            self._ocp_running = False
            self.ocp_label.setText("---")
            self.info_view.append(
                f"COMMUNICATION ERROR: Lost serial connection while stopping OCP: {exc}"
            )
            if state.ser and state.ser.is_connected:
                state.ser.disconnect_serial()
            self._show_status("Serial connection was lost. Reconnect before continuing.")
            return False

        self._ocp_running = False
        self.ocp_label.setText("---")
        return True

    def _poll_ocp(self):
        if state.ser is None:
            return
        try:
            status = state.ser.get_proc()
            if status in ("SERIAL_ERROR", "DISCONNECT"):
                logger.error("Serial worker stopped during OCP; disconnecting.")
                self._ocp_running = False
                self._ocp_timer.stop()
                state.ser.disconnect_serial()
                return

            while True:
                value = state.ser.get_data()
                if value is None:
                    break
                if isinstance(value, str):
                    logger.error("Serial worker stopped during OCP: %s", value)
                    self._ocp_running = False
                    self._ocp_timer.stop()
                    if state.ser and state.ser.is_connected:
                        state.ser.disconnect_serial()
                    return
                self.ocp_label.setText(f"{float(value):.4f} V")
        except Exception:
            logger.exception("Serial communication failed while polling OCP")
            self._ocp_running = False
            self._ocp_timer.stop()
            if state.ser and state.ser.is_connected:
                state.ser.disconnect_serial()

    # ------------------------------------------------------------------
    # Protocol terminal
    # ------------------------------------------------------------------

    def _poll_trace(self):
        """Move queued protocol entries from the worker into the panel."""
        serial_connection = state.ser
        if serial_connection is None:
            return
        try:
            entries = serial_connection.get_trace()
        except Exception:
            logger.exception("Could not read the protocol trace")
            return
        for kind, text in entries:
            self.protocol_view.append(kind, text)

    @pyqtSlot(bool)
    def _toggle_protocol_panel(self, checked: bool):
        self.protocol_view.setVisible(checked)

    def _on_theme_change(self, mode: str):
        from .theme_manager import save_preference, apply_theme
        save_preference(mode)
        app = QApplication.instance()
        apply_theme(app, mode)
        try:
            self.plot_widget.apply_theme()
        except Exception:
            pass
        for m, act in self._theme_actions.items():
            act.setChecked(m == mode)

    # ------------------------------------------------------------------
    # Experiment execution
    # ------------------------------------------------------------------

    def _build_parameters(self) -> dict:
        """Collect all UI parameter values into a single dict."""
        p = {}
        p.update(self.exp_panel.get_params())

        # ADC
        p["adc_pga"]     = ADC_PGA[self.adc_pga_combo.currentIndex()][1]
        p["adc_rate"]    = ADC_RATES[self.adc_rate_combo.currentIndex()][1]
        p["buffer_true"] = self.buffer_check.isChecked()
        p["short_true"]  = self.short_check.isChecked()

        # Gain
        p["gain"]        = self.gain_combo.currentData() or 2

        return p

    @pyqtSlot()
    def _on_execute(self):
        if state.ser is None or not state.ser.is_connected:
            self._show_status("Not connected.")
            return

        params = self._build_parameters()
        exp_id = self.exp_panel.current_id
        iface  = self.exp_panel.current_interface

        try:
            validation.validate(exp_id, params)
        except InputError as e:
            self._show_status(f"Invalid parameters: {e}")
            self.info_view.append(f"PARAMETER ERROR: {e}")
            QMessageBox.warning(self, "Invalid parameters", str(e))
            return

        if exp_id == "pot" and not comm.supports_ocp():
            msg = "v1.1 boards do not support potentiometry."
            self._show_status(msg)
            self.info_view.append(f"ERROR: {msg}")
            return

        try:
            self.current_exp = iface.get_experiment(params)
        except Exception as e:
            self._show_status(f"Parameter error: {e}")
            logger.error("Parameter error: %s", e)
            return

        # Setup plot
        plot_format = {}
        for plot_box in self.current_exp.plots:
            plot_format.update(plot_box.plot_format)
        if plot_format:
            self.plot_widget.setup_axes(plot_format)

        self._log_commands()

        self.data_view.clear()
        self.progress_bar.setValue(0)

        # The OCP readout owns the serial port, so stop it and clear the pipes
        # before handing over to the real experiment.
        if not self._stop_ocp():
            return
        try:
            state.ser.flush_data()
            state.ser.flush_proc()
        except (comm.ConnectionError, EOFError, OSError, ValueError) as exc:
            logger.exception("Serial connection was lost before experiment startup")
            self.info_view.append(f"COMMUNICATION ERROR: {exc}")
            if state.ser and state.ser.is_connected:
                state.ser.disconnect_serial()
            self._show_status("Serial connection was lost. Reconnect before continuing.")
            return

        self.btn_execute.setEnabled(False)
        self.btn_stop.setEnabled(True)

        # Start experiment in subprocess
        try:
            state.ser.start_exp(self.current_exp)
        except (comm.ConnectionError, EOFError, OSError, ValueError) as exc:
            logger.exception("Could not start experiment")
            self.info_view.append(f"COMMUNICATION ERROR: {exc}")
            if state.ser and state.ser.is_connected:
                state.ser.disconnect_serial()
            self.btn_execute.setEnabled(False)
            self.btn_stop.setEnabled(False)
            self._show_status("Serial connection was lost. Reconnect before continuing.")
            return

        # Start polling loop
        callbacks = {
            "experiment_done": self._on_experiment_done,
            "progress_update": self._on_progress_update,
        }
        self.current_loop = BaseLoop(self.current_exp, callbacks)
        self.current_loop.completion_error.connect(self._on_experiment_completion_error)
        self.current_loop.run()

        self._show_status("Experiment running…")

    @pyqtSlot()
    def _on_stop(self):
        if state.ser and state.ser.is_connected:
            state.ser.stop_exp()
        self._show_status("Stop requested.")

    @pyqtSlot()
    def _on_experiment_done(self):
        self.btn_execute.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress_bar.setValue(100)
        # Keep a reference so Analysis → Run Analysis can use it
        self._last_experiment = self.current_exp

        try:
            self._update_plot()
            self._populate_data_view()

            if self.autosave_check.isChecked():
                self._autosave()
        except Exception as exc:
            logger.exception("Failed to update the GUI after experiment completion")
            self.info_view.append(f"COMPLETION ERROR: {exc}")
            self._show_status(f"Experiment finished, but displaying its results failed: {exc}")
        else:
            if self.current_loop and self.current_loop.serial_error:
                self.info_view.append(
                    "Serial communication failed. The connection was closed; "
                    "reconnect before starting another experiment."
                )
            else:
                self._show_status("Experiment complete.")
        finally:
            if self.current_loop and self.current_loop.serial_error:
                if state.ser and state.ser.is_connected:
                    state.ser.disconnect_serial()
                self._show_status(
                    "Serial communication failed. Reconnect to continue."
                )
            else:
                self._start_ocp()

    @pyqtSlot(str)
    def _on_experiment_completion_error(self, message: str):
        self.info_view.append(f"COMPLETION ERROR: {message}")
        self._show_status(f"Experiment finished with a data finalization error: {message}")

    @pyqtSlot(float)
    def _on_progress_update(self, value: float):
        self.progress_bar.setValue(int(value * 100))
        self._update_plot()

    def _log_commands(self):
        """Record the exact command strings sent to the DStat in the Info tab."""
        if self.current_exp is None:
            return
        commands = getattr(self.current_exp, "commands", None) or []
        self.info_view.append(
            f"--- {self.exp_panel.current_id.upper()} command sequence ---"
        )
        for cmd in commands:
            if isinstance(cmd, str):
                self.info_view.append(f"  {cmd.strip()}")
            else:
                self.info_view.append(f"  {cmd[0].strip()} {cmd[1]}")

    def _update_plot(self):
        if self.current_exp is None:
            return
        for key, data in self.current_exp.data.items():
            for scan_idx, scan in enumerate(data):
                if len(scan) >= 2 and len(scan[0]) > 0:
                    self.plot_widget.update_data(key, scan[0], scan[1], scan_idx)

    def _populate_data_view(self):
        if self.current_exp is None:
            return
        try:
            columns = self.current_exp.columns
            # Flatten first data channel for display
            first_key = next(iter(self.current_exp.data))
            scans = self.current_exp.data[first_key]
            rows = []
            for scan_idx, scan in enumerate(scans):
                pairs = list(zip(*scan))
                for row in pairs:
                    rows.append(row)
            self.data_view.populate(columns, rows)
        except Exception as e:
            logger.warning("Could not populate data view: %s", e)

    # ------------------------------------------------------------------
    # Autosave
    # ------------------------------------------------------------------

    def _autosave(self):
        directory = self.autosave_dir.text() or os.path.expanduser("~")
        base_name = self.autosave_name.text() or "experiment"
        counter = self._autosave_counter.get(base_name, 0)

        # Find a non-colliding filename
        while True:
            stem = f"{base_name}_{counter:04d}"
            path = os.path.join(directory, stem + ".txt")
            if not os.path.exists(path):
                break
            counter += 1

        self._autosave_counter[base_name] = counter + 1

        try:
            from .save_dialog import _save_text
            _save_text(self.current_exp, path)
            self._show_status(f"Autosaved to {path}")
        except Exception as e:
            logger.error("Autosave failed: %s", e)

    # ------------------------------------------------------------------
    # Menu actions
    # ------------------------------------------------------------------

    def _on_save_data(self):
        if self.current_exp is None:
            self._show_status("No data to save.")
            return
        save_dialog.save_data_dialog(self, self.current_exp)

    def _on_save_plot(self):
        save_dialog.save_plot_dialog(self, self.plot_widget)

    def _on_save_params(self):
        params = self._build_parameters()
        params["experiment_index"] = self.exp_panel.current_id
        save_dialog.save_params_dialog(self, params)

    def _on_load_params(self):
        params = save_dialog.load_params_dialog(self)
        if params is None:
            return
        exp_id = params.get("experiment_index")
        if exp_id:
            self.exp_panel.set_params(exp_id, params)

    # ------------------------------------------------------------------
    # Dropbot slots
    # ------------------------------------------------------------------

    def _on_dropbot_connect(self):
        """Start listening for a µDrop ZMQ connection."""
        if not _ZMQ_AVAILABLE:
            QMessageBox.warning(self, "Dropbot",
                                "The 'zmq' package is not installed.\n"
                                "Install it with:  pip install pyzmq")
            return
        try:
            from ..microdrop import microdropConnection
            self._dropbot = microdropConnection()
            self._dropbot_connected = True
            self._act_dropbot_connect.setEnabled(False)
            self._act_dropbot_disconnect.setEnabled(True)
            self._show_status("Dropbot: listening on port 6789")
        except Exception as exc:
            QMessageBox.critical(self, "Dropbot Error", str(exc))

    def _on_dropbot_disconnect(self):
        """Disconnect from µDrop."""
        self._dropbot_connected = False
        self._act_dropbot_connect.setEnabled(True)
        self._act_dropbot_disconnect.setEnabled(False)
        self._show_status("Dropbot: disconnected")

    # ------------------------------------------------------------------
    # Analysis slots
    # ------------------------------------------------------------------

    def _on_analysis_options(self):
        """Open the Analysis Options dialog."""
        self._analysis_dialog.exec()

    def _on_run_analysis(self):
        """Run analysis on the most recent experiment data."""
        exp = getattr(self, "_last_experiment", None)
        if exp is None:
            QMessageBox.information(self, "Analysis",
                                    "No experiment data available yet.")
            return
        results = do_analysis(exp, self._analysis_dialog.params)
        if not results:
            msg = "No analysis results (enable Statistics in Analysis Options)."
        else:
            lines = []
            for ch, txt in results.items():
                lines.append(f"=== {ch} ===\n{txt}")
            msg = "\n\n".join(lines)
        QMessageBox.information(self, "Analysis Results", msg)

    # ------------------------------------------------------------------
    # Experiment Guide
    # ------------------------------------------------------------------

    def _on_experiment_guide(self):
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser
        dlg = QDialog(self)
        dlg.setWindowTitle("Experiment Guide")
        dlg.resize(700, 560)

        layout = QVBoxLayout(dlg)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(_EXPERIMENT_GUIDE_HTML)
        layout.addWidget(browser)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        dlg.exec()

    # ------------------------------------------------------------------
    # About
    # ------------------------------------------------------------------

    def _on_about(self):
        QMessageBox.about(
            self,
            "About DStat Interface",
            (
                "<b>DStat Interface</b><br>"
                f"Version {VERSION}<br><br>"
                "Python 3 / Qt6 rewrite of the original GTK-based interface.<br><br>"
                "Original code by Michael D. M. Dryden,<br>"
                "Wheeler Microfluidics Laboratory, University of Toronto.<br><br>"
                "Published under the GNU GPL v3."
            ),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _show_status(self, message: str):
        self.status_bar.showMessage(message)
        logger.info(message)

    def _browse_autosave_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Save Directory", os.path.expanduser("~")
        )
        if directory:
            self.autosave_dir.setText(directory)

    def _shutdown_serial_connection(self):
        self._ocp_timer.stop()
        trace_timer = getattr(self, "_trace_timer", None)
        if trace_timer is not None:
            trace_timer.stop()
        if self.current_loop:
            self.current_loop._stop_timers()
        if state.ser:
            state.ser.disconnect_serial()

    def closeEvent(self, event):
        self._shutdown_serial_connection()
        event.accept()
