"""Calibration dialog for DStat EEPROM settings.

Exposes the device's calibration/trim parameters (DAC offset, per-gain current
trims, EIS constants, light sensor, DAC units mode) and writes them back to
the DStat EEPROM through the existing ``SW`` command.
"""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QSpinBox, QCheckBox, QPushButton, QDialogButtonBox, QMessageBox,
    QScrollArea, QWidget,
)
from PyQt6.QtCore import Qt
from collections import OrderedDict

from ..dstat import state, comm

logger = logging.getLogger(__name__)

GAIN_TRIMS = [
    ("r100_trim", "100 Ω gain trim"),
    ("r3k_trim", "3 kΩ gain trim"),
    ("r30k_trim", "30 kΩ gain trim"),
    ("r300k_trim", "300 kΩ gain trim"),
    ("r3M_trim", "3 MΩ gain trim"),
    ("r30M_trim", "30 MΩ gain trim"),
    ("r100M_trim", "100 MΩ gain trim"),
]


class CalibrationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calibration / Device Settings")
        self.resize(460, 620)
        self.setModal(True)

        self._fields: dict[str, object] = {}

        # Brief procedure hint at the top.
        hint = QLabel(
            "Procedimiento breve:\n"
            "1. Conectá el DStat y pulsá «Read from device».\n"
            "2. DAC offset: medí el pin DAC_OUT con multímetro; ajustá hasta que "
            "0 mV → 1.500 V.\n"
            "3. Gain trims: con electrodos al aire (Ropen) o resistor conocido, "
            "ajustá cada trim hasta que la corriente coincida con la Ley de Ohm.\n"
            "4. Pulsá «Write to device» para guardar en EEPROM.\n"
            "5. Verificá con tools/analyze_signals.py."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("background:#f0fdfa; border:1px solid #0d9488; "
                           "border-radius:6px; padding:8px; font-size:9pt;")

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)

        # --- DAC ---
        dac_grp = QGroupBox("DAC (MAX5443)")
        dac_form = QFormLayout(dac_grp)
        self._fields["max5443_offset"] = QSpinBox()
        self._fields["max5443_offset"].setRange(-32767, 32767)
        self._fields["max5443_offset"].setToolTip(
            "Offset applied to every DAC code (DAC units). Corrects the "
            "voltage baseline."
        )
        dac_form.addRow("DAC offset:", self._fields["max5443_offset"])

        dac_hint = QLabel("Unidades DAC (±32767). 0 = sin corrección. Corrige el "
                          "offset de tensión del DAC MAX5443.")
        dac_hint.setWordWrap(True)
        dac_hint.setStyleSheet("color:#6b7280; font-size:8pt;")
        dac_form.addRow("", dac_hint)

        self._fields["dac_units_true"] = QCheckBox("Firmware expects DAC units (not mV)")
        self._fields["dac_units_true"].setToolTip(
            "When enabled the host must send DAC indexes instead of mV."
        )
        dac_form.addRow("", self._fields["dac_units_true"])
        layout.addWidget(dac_grp)

        # --- Current trims ---
        trim_grp = QGroupBox("Current gain trims (ADC counts)")
        trim_form = QFormLayout(trim_grp)
        for key, label in GAIN_TRIMS:
            sb = QSpinBox()
            sb.setRange(-32767, 32767)
            sb.setToolTip(
                "Offset added to the ADC code for this gain. Calibrate with a "
                "known resistor: adjust until reported current matches Ohm."
            )
            self._fields[key] = sb
            trim_form.addRow(label + ":", sb)
        trim_hint = QLabel("Unidades ADC (±32767). 0 = sin corrección. Ajustar con "
                           "resistor conocido o Ropen hasta que la corriente "
                           "coincida con la Ley de Ohm.")
        trim_hint.setWordWrap(True)
        trim_hint.setStyleSheet("color:#6b7280; font-size:8pt;")
        trim_form.addRow("", trim_hint)
        layout.addWidget(trim_grp)

        # --- EIS ---
        eis_grp = QGroupBox("EIS calibration")
        eis_form = QFormLayout(eis_grp)
        self._fields["eis_cal1"] = QSpinBox()
        self._fields["eis_cal1"].setRange(0, 2_000_000_000)
        eis_form.addRow("EIS cal 1:", self._fields["eis_cal1"])

        self._fields["eis_cal2"] = QSpinBox()
        self._fields["eis_cal2"].setRange(0, 2_000_000_000)
        eis_form.addRow("EIS cal 2:", self._fields["eis_cal2"])
        eis_hint = QLabel("Constantes de calibración para EIS. Default: 3000 y 3000000.")
        eis_hint.setWordWrap(True)
        eis_hint.setStyleSheet("color:#6b7280; font-size:8pt;")
        eis_form.addRow("", eis_hint)
        layout.addWidget(eis_grp)

        # --- Light sensor ---
        tcs_grp = QGroupBox("Light sensor (TCS)")
        tcs_form = QFormLayout(tcs_grp)
        self._fields["tcs_enabled"] = QCheckBox("Enabled")
        tcs_form.addRow("TCS:", self._fields["tcs_enabled"])

        self._fields["tcs_clear_threshold"] = QSpinBox()
        self._fields["tcs_clear_threshold"].setRange(0, 100_000)
        tcs_form.addRow("Clear threshold:", self._fields["tcs_clear_threshold"])
        layout.addWidget(tcs_grp)

        layout.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.addWidget(hint)
        outer.addWidget(scroll)

        # --- Buttons ---
        btns = QHBoxLayout()
        self.btn_read = QPushButton("Read from device")
        self.btn_read.clicked.connect(self._read)
        btns.addWidget(self.btn_read)

        self.btn_defaults = QPushButton("Restore defaults")
        self.btn_defaults.clicked.connect(self._restore_defaults)
        btns.addWidget(self.btn_defaults)

        self.btn_write = QPushButton("Write to device")
        self.btn_write.setObjectName("btn_execute")
        self.btn_write.clicked.connect(self._write)
        btns.addWidget(self.btn_write)

        outer.addLayout(btns)

        note = QLabel(
            "Values are stored in the DStat EEPROM and persist across power "
            "cycles. 'Restore defaults' resets every parameter to the firmware "
            "defaults."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #6b7280; font-size: 9pt;")
        outer.addWidget(note)

        self._load_from_state()

    # ------------------------------------------------------------------
    def _load_from_state(self):
        settings = getattr(state, "settings", None) or {}
        for key, widget in self._fields.items():
            entry = settings.get(key)
            val = entry[1] if (isinstance(entry, (list, tuple)) and len(entry) > 1) else None
            if val is None:
                continue
            if isinstance(widget, QCheckBox):
                widget.setChecked(bool(val))
            else:
                try:
                    widget.setValue(int(val))
                except (TypeError, ValueError):
                    pass

    def _read(self):
        if state.ser is None or not getattr(state.ser, "is_connected", False):
            QMessageBox.warning(self, "Not connected", "Connect to the DStat first.")
            return
        try:
            comm.read_settings()
        except Exception as exc:
            QMessageBox.critical(self, "Read failed", str(exc))
            return
        self._load_from_state()
        QMessageBox.information(self, "Read", "Settings read from device.")

    def _collect(self) -> dict:
        out = {}
        for key, widget in self._fields.items():
            if isinstance(widget, QCheckBox):
                out[key] = 1 if widget.isChecked() else 0
            else:
                out[key] = int(widget.value())
        return out

    def _write(self):
        if state.ser is None or not getattr(state.ser, "is_connected", False):
            QMessageBox.warning(self, "Not connected", "Connect to the DStat first.")
            return
        values = self._collect()
        # Rebuild state.settings in the firmware's expected order.
        ordered = {}
        # Preserve existing entries not in dialog (keep their index).
        for k, v in (state.settings or {}).items():
            ordered[k] = list(v) if isinstance(v, (list, tuple)) else [0, v]
        for k, v in values.items():
            if k in ordered:
                ordered[k][1] = v
            else:
                ordered[k] = [0, v]
        # Ensure all SETTINGS_ORDER keys exist
        for k in comm.SETTINGS_ORDER:
            if k not in ordered:
                ordered[k] = [0, 0]
            ordered[k][1] = values.get(k, ordered[k][1])
        state.settings = OrderedDict(ordered)
        try:
            comm.write_settings()
        except Exception as exc:
            QMessageBox.critical(self, "Write failed", str(exc))
            return
        self._load_from_state()
        QMessageBox.information(self, "Written", "Settings written to EEPROM.")

    def _restore_defaults(self):
        if state.ser is None or not getattr(state.ser, "is_connected", False):
            QMessageBox.warning(self, "Not connected", "Connect to the DStat first.")
            return
        reply = QMessageBox.question(
            self, "Restore defaults",
            "Reset all EEPROM settings to firmware defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        defaults = {
            "max5443_offset": 0,
            "tcs_enabled": 1,
            "tcs_clear_threshold": 10000,
            "r100_trim": 0, "r3k_trim": 0, "r30k_trim": 0,
            "r300k_trim": 0, "r3M_trim": 0, "r30M_trim": 0,
            "r100M_trim": 0,
            "eis_cal1": 3000, "eis_cal2": 3000000,
            "dac_units_true": 0,
        }
        for k, v in defaults.items():
            if k in self._fields:
                w = self._fields[k]
                if isinstance(w, QCheckBox):
                    w.setChecked(bool(v))
                else:
                    w.setValue(int(v))
        self._write()
