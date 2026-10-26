"""Calibration dialog for DStat EEPROM settings.

Exposes the device's calibration/trim parameters (DAC offset, per-gain current
trims, EIS constants, light sensor, DAC units mode) and writes them back to
the DStat EEPROM through the existing ``SW`` command.
"""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QSpinBox, QCheckBox, QPushButton, QMessageBox,
    QScrollArea, QWidget, QProgressBar,
)
from PyQt6.QtCore import Qt, QEventLoop, QTimer
from collections import OrderedDict

from ..dstat import state, comm
from ..experiments.calib import CalibExp
from .theme_manager import resolved_palette

logger = logging.getLogger(__name__)

GAIN_TRIMS = [
    ("r100_trim", "100 ohm gain trim"),
    ("r3k_trim", "3 kohm gain trim"),
    ("r30k_trim", "30 kohm gain trim"),
    ("r300k_trim", "300 kohm gain trim"),
    ("r3M_trim", "3 Mohm gain trim"),
    ("r30M_trim", "30 Mohm gain trim"),
    ("r100M_trim", "100 Mohm gain trim"),
]


class CalibrationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calibration / Device Settings")
        self.resize(460, 620)
        self.setModal(True)

        self._fields: dict[str, object] = {}

        palette = resolved_palette()
        muted = palette.fg_muted
        accent = palette.input_focus

        # Brief procedure hint at the top.
        hint = QLabel(
            "Quick procedure:\n"
            "1. Connect the DStat and click 'Read from device'.\n"
            "2. DAC offset: measure the DAC_OUT pin with a multimeter; adjust "
            "until 0 mV -> 1.500 V.\n"
            "3. Gain trims: with electrodes in air (Ropen) or a known resistor, "
            "adjust each trim until the reported current matches Ohm's law.\n"
            "4. Click 'Write to device' to save to EEPROM.\n"
            "5. Verify with tools/analyze_signals.py."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "background: transparent; border: 1px solid %s; "
            "border-radius: 6px; padding: 8px; font-size: 9pt; color: %s;"
            % (accent, palette.fg)
        )

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

        dac_hint = QLabel("DAC units (+-32767). 0 = no correction. Corrects the "
                          "voltage offset of the MAX5443 DAC.")
        dac_hint.setWordWrap(True)
        dac_hint.setStyleSheet("color: %s; font-size: 8pt;" % muted)
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

        self._calib_time = QSpinBox()
        self._calib_time.setRange(1, 65535)
        self._calib_time.setValue(10)
        self._calib_time.setToolTip(
            "Duration (s) of the 0 mV calibration step per gain."
        )
        trim_form.addRow("Calibration time (s):", self._calib_time)

        for key, label in GAIN_TRIMS:
            sb = QSpinBox()
            sb.setRange(-32767, 32767)
            sb.setToolTip(
                "Offset added to the ADC code for this gain. Calibrate with a "
                "known resistor: adjust until reported current matches Ohm."
            )
            self._fields[key] = sb
            trim_form.addRow(label + ":", sb)
        trim_hint = QLabel("ADC units (+-32767). 0 = no correction. Adjust with a "
                           "known resistor or Ropen until the current matches "
                           "Ohm's law.")
        trim_hint.setWordWrap(True)
        trim_hint.setStyleSheet("color: %s; font-size: 8pt;" % muted)
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
        eis_hint = QLabel("EIS calibration constants. Default: 3000 and 3000000.")
        eis_hint.setWordWrap(True)
        eis_hint.setStyleSheet("color: %s; font-size: 8pt;" % muted)
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

        self.btn_measure = QPushButton("Measure (auto-calibrate)")
        self.btn_measure.clicked.connect(self._measure)
        btns.addWidget(self.btn_measure)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Idle")
        outer.addWidget(self.progress_bar)

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
        note.setStyleSheet("color: %s; font-size: 9pt;" % muted)
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

    def _measure(self):
        if state.ser is None or not getattr(state.ser, "is_connected", False):
            QMessageBox.warning(self, "Not connected", "Connect to the DStat first.")
            return
        reply = QMessageBox.question(
            self, "Auto-calibrate",
            "Run calibration for all 7 gains? This takes about "
            "%d seconds per gain." % self._calib_time.value(),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        time_val = int(self._calib_time.value())
        gain_trim_table = [None, "r100_trim", "r3k_trim", "r30k_trim",
                           "r300k_trim", "r3M_trim", "r30M_trim", "r100M_trim"]

        # Stop OCP if running (best effort)
        try:
            if hasattr(self.parent(), "_stop_ocp"):
                self.parent()._stop_ocp()
        except Exception:
            pass

        self.btn_measure.setEnabled(False)
        self.btn_read.setEnabled(False)
        self.btn_write.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Starting...")
        errors = []
        total_gains = 7
        for i, gain_idx in enumerate(range(1, 8)):
            self.progress_bar.setFormat("Measuring gain %d/7..." % (i + 1))
            self.progress_bar.setValue(int(i / total_gains * 100))
            try:
                state.ser.flush_data()
                state.ser.flush_proc()
                exp = CalibExp({"gain": gain_idx, "time": time_val})
                state.ser.start_exp(exp)

                # Poll manually (no BaseLoop) so we can capture the offset.
                ev = QEventLoop()
                serial_error = {"v": False}
                offset_holder = {"v": None}

                def poll():
                    try:
                        # data
                        incoming = state.ser.get_data()
                        while incoming is not None:
                            # CalibExp sends the averaged offset as a single int
                            # via data_pipe at @DONE. Capture it.
                            if isinstance(incoming, int):
                                offset_holder["v"] = incoming
                            elif isinstance(incoming, (list, tuple)) and len(incoming) == 1 and isinstance(incoming[0], int):
                                offset_holder["v"] = incoming[0]
                            incoming = state.ser.get_data()
                        # proc
                        proc = state.ser.get_proc()
                        if proc is not None:
                            if proc in ("DONE", "SERIAL_ERROR", "ABORT"):
                                if proc == "SERIAL_ERROR":
                                    serial_error["v"] = True
                                ev.quit()
                    except Exception as exc:
                        logger.exception("poll error: %s", exc)
                        ev.quit()

                timer = QTimer(self)
                timer.timeout.connect(poll)
                timer.start(50)
                ev.exec()
                timer.stop()

                if serial_error["v"]:
                    errors.append("gain %d: serial error" % gain_idx)
                    continue

                offset = offset_holder["v"]
                if offset is None:
                    # try one last blocking read
                    try:
                        offset = state.ser.get_data(block=True, timeout=5)
                    except Exception:
                        offset = None
                if offset is None:
                    errors.append("gain %d: no data" % gain_idx)
                    continue
                trim = -int(offset)
                trim = max(-32767, min(32767, trim))
                key = gain_trim_table[gain_idx]
                if key in self._fields:
                    self._fields[key].setValue(trim)
            except Exception as exc:
                errors.append("gain %d: %s" % (gain_idx, exc))
                logger.exception("Auto-calibrate gain %d failed", gain_idx)
            self.progress_bar.setValue(int((i + 1) / total_gains * 100))

        self.progress_bar.setFormat("Done")
        self.btn_measure.setEnabled(True)
        self.btn_read.setEnabled(True)
        self.btn_write.setEnabled(True)

        # Restart OCP (best effort)
        try:
            if hasattr(self.parent(), "_start_ocp"):
                self.parent()._start_ocp()
        except Exception:
            pass

        if errors:
            QMessageBox.warning(self, "Auto-calibrate",
                                "Completed with errors:\n" + "\n".join(errors))
        else:
            QMessageBox.information(self, "Auto-calibrate",
                                    "Calibration offsets measured. Review and "
                                    "click 'Write to device' to save.")