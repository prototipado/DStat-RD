"""Experiment panel widgets.

Each concrete `ExpInterface` subclass creates a small `QWidget` with the
parameter fields for one technique.  The `ExperimentsPanel` collects them
all and exposes a combo-box that swaps the visible panel.
"""

import logging
from collections import OrderedDict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QStackedWidget, QGroupBox,
    QCheckBox, QSpinBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QAbstractItemView,
)
from PyQt6.QtCore import pyqtSignal, QObject, Qt

from ..experiments import cv, lsv, swv, dpv, chronoamp, pot

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base experiment interface widget
# ---------------------------------------------------------------------------

class ExpInterface(QWidget):
    """Base class for experiment parameter widgets."""

    id = None
    name = "Unknown"
    experiment_class = None  # concrete Experiment subclass

    def __init__(self, parent=None):
        super().__init__(parent)
        self.entry: dict[str, QLineEdit] = {}
        self._setup_ui()

    def _setup_ui(self):
        """Override in subclasses to build the form."""
        pass

    @property
    def params(self) -> dict:
        return {k: v.text() for k, v in self.entry.items()}

    @params.setter
    def params(self, values: dict):
        for k, field in self.entry.items():
            if k in values:
                field.setText(str(values[k]))

    def get_experiment(self, parameters: dict):
        return self.__class__.experiment_class(parameters)

    def _make_field(self, default: str = "0") -> QLineEdit:
        return QLineEdit(default)

    def _add_field(self, layout: QFormLayout, label: str, key: str, default: str = "0"):
        field = self._make_field(default)
        layout.addRow(label, field)
        self.entry[key] = field
        return field

    def _build_preconditioning_group(self) -> QGroupBox:
        """Shared 'Preconditioning' group: Cleaning and Deposition rows."""
        grp = QGroupBox("Preconditioning")
        grid = QGridLayout(grp)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        grid.addWidget(QLabel("Potential (mV)"), 0, 1, Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(QLabel("Time (s)"),        0, 2, Qt.AlignmentFlag.AlignCenter)

        grid.addWidget(QLabel("Cleaning"),   1, 0)
        clean_mV = self._make_field("0")
        clean_s  = self._make_field("0")
        grid.addWidget(clean_mV, 1, 1)
        grid.addWidget(clean_s,  1, 2)
        self.entry["clean_mV"] = clean_mV
        self.entry["clean_s"]  = clean_s

        grid.addWidget(QLabel("Deposition"), 2, 0)
        dep_mV = self._make_field("0")
        dep_s  = self._make_field("0")
        grid.addWidget(dep_mV, 2, 1)
        grid.addWidget(dep_s,  2, 2)
        self.entry["dep_mV"] = dep_mV
        self.entry["dep_s"]  = dep_s

        return grp

    def _build_experiment_group(self, title: str = "Experiment") -> tuple:
        """Return (QGroupBox, QFormLayout) for technique-specific params."""
        grp = QGroupBox(title)
        form = QFormLayout(grp)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        return grp, form


# ---------------------------------------------------------------------------
# CV
# ---------------------------------------------------------------------------

class CVInterface(ExpInterface):
    id = "cve"
    name = "Cyclic Voltammetry"
    experiment_class = cv.CVExp

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        pre_grp = self._build_preconditioning_group()
        layout.addWidget(pre_grp)

        exp_grp, form = self._build_experiment_group()
        self._add_field(form, "Start (mV):",    "start", "0")
        self._add_field(form, "Vertex 1 (mV):", "v1",    "500")
        self._add_field(form, "Vertex 2 (mV):", "v2",    "-500")
        self._add_field(form, "Slope (mV/s):",  "slope", "100")
        self._add_field(form, "Scans:",          "scans", "1")
        layout.addWidget(exp_grp)


# ---------------------------------------------------------------------------
# LSV
# ---------------------------------------------------------------------------

class LSVInterface(ExpInterface):
    id = "lsv"
    name = "Linear Sweep Voltammetry"
    experiment_class = lsv.LSVExp

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        pre_grp = self._build_preconditioning_group()
        layout.addWidget(pre_grp)

        exp_grp, form = self._build_experiment_group()
        self._add_field(form, "Start (mV):",   "start", "-200")
        self._add_field(form, "Stop (mV):",    "stop",  "200")
        self._add_field(form, "Slope (mV/s):", "slope", "100")
        layout.addWidget(exp_grp)


# ---------------------------------------------------------------------------
# SWV
# ---------------------------------------------------------------------------

class SWVInterface(ExpInterface):
    id = "swv"
    name = "Square Wave Voltammetry"
    experiment_class = swv.SWVExp

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        pre_grp = self._build_preconditioning_group()
        layout.addWidget(pre_grp)

        exp_grp, form = self._build_experiment_group()
        self._add_field(form, "Start (mV):",     "start", "0")
        self._add_field(form, "Stop (mV):",      "stop",  "500")
        self._add_field(form, "Step (mV):",      "step",  "2")
        self._add_field(form, "Pulse (mV):",     "pulse", "25")
        self._add_field(form, "Frequency (Hz):", "freq",  "25")
        self._add_field(form, "Scans:",          "scans", "1")
        layout.addWidget(exp_grp)


# ---------------------------------------------------------------------------
# DPV
# ---------------------------------------------------------------------------

class DPVInterface(ExpInterface):
    id = "dpv"
    name = "Differential Pulse Voltammetry"
    experiment_class = dpv.DPVExp

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        pre_grp = self._build_preconditioning_group()
        layout.addWidget(pre_grp)

        exp_grp, form = self._build_experiment_group()
        self._add_field(form, "Start (mV):",   "start",  "0")
        self._add_field(form, "Stop (mV):",    "stop",   "500")
        self._add_field(form, "Step (mV):",    "step",   "2")
        self._add_field(form, "Pulse (mV):",   "pulse",  "25")
        self._add_field(form, "Period (ms):",  "period", "200")
        self._add_field(form, "Width (ms):",   "width",  "50")
        width_field = self.entry["width"]
        width_field.setToolTip(
            "Must be shorter than the period.\n"
            "Note: the ADC samples 1/(ADC rate) before the end of the pulse, "
            "so the sample period should be well below the pulse width to "
            "limit capacitive current."
        )
        layout.addWidget(exp_grp)


# ---------------------------------------------------------------------------
# Chronoamperometry
# ---------------------------------------------------------------------------

class ChronoampInterface(ExpInterface):
    id = "cae"
    name = "Chronoamperometry"
    experiment_class = chronoamp.Chronoamp

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Input row ──────────────────────────────────────────────
        input_row = QHBoxLayout()
        input_row.addWidget(QLabel("Potential (mV):"))
        self._pot_input = QLineEdit("0")
        self._pot_input.setFixedWidth(70)
        input_row.addWidget(self._pot_input)

        input_row.addWidget(QLabel("Time (s):"))
        self._time_input = QLineEdit("0")
        self._time_input.setFixedWidth(70)
        input_row.addWidget(self._time_input)
        layout.addLayout(input_row)

        # ── Add / Remove buttons ────────────────────────────────────
        btn_row = QHBoxLayout()
        self._btn_add = QPushButton("+ Add")
        self._btn_add.clicked.connect(self._add_row)
        self._btn_remove = QPushButton("− Remove")
        self._btn_remove.clicked.connect(self._remove_row)
        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_remove)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── Steps table ─────────────────────────────────────────────
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Time (s)", "Potential (mV)"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self._table.setFixedHeight(150)
        layout.addWidget(self._table)

        # Seed with one default step (a 0 s step would be rejected by validation)
        self._insert_row(0.0, 10)

    def _insert_row(self, potential: float, time: int):
        row = self._table.rowCount()
        self._table.insertRow(row)
        pot_item  = QTableWidgetItem(str(potential))
        time_item = QTableWidgetItem(str(time))
        pot_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, 0, time_item)
        self._table.setItem(row, 1, pot_item)

    def _add_row(self):
        try:
            pot  = float(self._pot_input.text())
            time = int(self._time_input.text())
        except ValueError:
            return
        self._insert_row(pot, time)

    def _remove_row(self):
        row = self._table.currentRow()
        if self._table.selectedItems() and row >= 0:
            self._table.removeRow(row)
        elif self._table.rowCount() > 0:
            self._table.removeRow(self._table.rowCount() - 1)

    @property
    def params(self) -> dict:
        potentials = []
        times = []
        for row in range(self._table.rowCount()):
            try:
                times.append(int(self._table.item(row, 0).text()))
                potentials.append(float(self._table.item(row, 1).text()))
            except (ValueError, AttributeError):
                pass
        return {
            "potential": potentials or [0.0],
            "time":      times      or [1],
        }

    @params.setter
    def params(self, values: dict):
        potentials = values.get("potential", [])
        times      = values.get("time", [])
        self._table.setRowCount(0)
        for pot, t in zip(potentials, times):
            self._insert_row(pot, t)


# ---------------------------------------------------------------------------
# Potentiometry
# ---------------------------------------------------------------------------

class PotInterface(ExpInterface):
    id = "pot"
    name = "Potentiometry"
    experiment_class = pot.PotExp

    def _setup_ui(self):
        form = QFormLayout(self)
        self._add_field(form, "Time (s):", "time", "60")


# ---------------------------------------------------------------------------
# Container panel
# ---------------------------------------------------------------------------

class ExperimentsPanel(QWidget):
    """Combo-box that switches between experiment parameter widgets."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._interfaces: OrderedDict[str, ExpInterface] = OrderedDict()

        # Register all techniques
        for cls in [CVInterface, LSVInterface, SWVInterface, DPVInterface,
                    ChronoampInterface, PotInterface]:
            inst = cls()
            self._interfaces[cls.id] = inst

        # Build UI
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.combo = QComboBox()
        for iface in self._interfaces.values():
            self.combo.addItem(iface.name, iface.id)
        self.combo.currentIndexChanged.connect(self._on_combo_changed)
        layout.addWidget(self.combo)

        self.stack = QStackedWidget()
        for iface in self._interfaces.values():
            self.stack.addWidget(iface)
        layout.addWidget(self.stack)

    def _on_combo_changed(self):
        exp_id = self.combo.currentData()
        idx = list(self._interfaces.keys()).index(exp_id)
        self.stack.setCurrentIndex(idx)

    @property
    def current_id(self) -> str:
        return self.combo.currentData()

    @property
    def current_interface(self) -> ExpInterface:
        return self._interfaces[self.current_id]

    def get_params(self) -> dict:
        return self.current_interface.params

    def set_params(self, exp_id: str, params: dict):
        if exp_id in self._interfaces:
            self._interfaces[exp_id].params = params
            idx = list(self._interfaces.keys()).index(exp_id)
            self.combo.setCurrentIndex(idx)
