"""Analysis options dialog and data analysis helpers.

Mirrors the original `analysis.py` AnalysisOptions class, ported to PyQt6.
"""

import logging

import numpy as np

# np.trapz was removed in NumPy 2.0
_trapezoid = getattr(np, "trapezoid", None) or np.trapz

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QCheckBox, QDoubleSpinBox, QDialogButtonBox, QLabel,
)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class AnalysisOptionsDialog(QDialog):
    """Dialog for configuring post-acquisition analysis options."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Analysis Options…")
        self.setModal(True)
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)

        # ── Statistics group ─────────────────────────────────────────
        stats_grp = QGroupBox("Statistics")
        stats_grp.setCheckable(True)
        stats_grp.setChecked(False)
        self._stats_grp = stats_grp
        stats_layout = QFormLayout(stats_grp)

        self._start_check = QCheckBox("Use custom start")
        self._start_check.stateChanged.connect(self._toggle_start)
        stats_layout.addRow(self._start_check)

        self._start_spin = QDoubleSpinBox()
        self._start_spin.setRange(-1e9, 1e9)
        self._start_spin.setDecimals(2)
        self._start_spin.setSingleStep(0.05)
        self._start_spin.setEnabled(False)
        stats_layout.addRow("Start:", self._start_spin)

        self._stop_check = QCheckBox("Use custom stop")
        self._stop_check.stateChanged.connect(self._toggle_stop)
        stats_layout.addRow(self._stop_check)

        self._stop_spin = QDoubleSpinBox()
        self._stop_spin.setRange(-1e9, 1e9)
        self._stop_spin.setDecimals(2)
        self._stop_spin.setSingleStep(0.05)
        self._stop_spin.setEnabled(False)
        stats_layout.addRow("Stop:", self._stop_spin)

        layout.addWidget(stats_grp)

        # ── OK button ────────────────────────────────────────────────
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------

    def _toggle_start(self, state):
        self._start_spin.setEnabled(bool(state))

    def _toggle_stop(self, state):
        self._stop_spin.setEnabled(bool(state))

    # ------------------------------------------------------------------
    # params property (same keys as the original GTK version)
    # ------------------------------------------------------------------

    @property
    def params(self) -> dict:
        return {
            "stats_true":       self._stats_grp.isChecked(),
            "stats_start_true": self._start_check.isChecked(),
            "stats_start":      self._start_spin.value(),
            "stats_stop_true":  self._stop_check.isChecked(),
            "stats_stop":       self._stop_spin.value(),
        }

    @params.setter
    def params(self, values: dict):
        self._stats_grp.setChecked(values.get("stats_true", False))
        self._start_check.setChecked(values.get("stats_start_true", False))
        self._start_spin.setValue(values.get("stats_start", 0.0))
        self._stop_check.setChecked(values.get("stats_stop_true", False))
        self._stop_spin.setValue(values.get("stats_stop", 0.0))


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------

def do_analysis(experiment, options: dict) -> dict:
    """Run selected analyses on *experiment* data.

    Returns a dict of result strings keyed by channel name.
    """
    results = {}

    if not options.get("stats_true"):
        return results

    for key, data in experiment.data.items():
        channel_results = []
        for scan_idx, scan in enumerate(data):
            if len(scan) < 2 or len(scan[0]) == 0:
                continue

            x = np.array(scan[0])
            y = np.array(scan[1])

            # Optionally slice to user-defined x range
            mask = np.ones(len(x), dtype=bool)
            if options.get("stats_start_true"):
                mask &= x >= options["stats_start"]
            if options.get("stats_stop_true"):
                mask &= x <= options["stats_stop"]

            x_sel = x[mask]
            y_sel = y[mask]

            if len(y_sel) == 0:
                continue

            result = (
                f"Scan {scan_idx}:  "
                f"mean={np.mean(y_sel):.4g}  "
                f"min={np.min(y_sel):.4g}  "
                f"max={np.max(y_sel):.4g}  "
                f"integral={_trapezoid(y_sel, x_sel):.4g}"
            )
            channel_results.append(result)

        if channel_results:
            results[key] = "\n".join(channel_results)

    return results
