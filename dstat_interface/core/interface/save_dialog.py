"""Save and load dialogs."""

import os
import logging

import numpy as np
import yaml

from PyQt6.QtWidgets import QFileDialog, QWidget

logger = logging.getLogger(__name__)


def save_data_dialog(parent: QWidget, experiment) -> None:
    """Open a file-save dialog and write experiment data as TSV."""
    path, selected_filter = QFileDialog.getSaveFileName(
        parent,
        "Save Data",
        os.path.expanduser("~"),
        "Tab-separated Text (*.txt);;NumPy binary (*.npy)",
    )
    if not path:
        return

    if selected_filter.endswith("(*.npy)"):
        _save_npy(experiment, path if path.endswith(".npy") else path + ".npy")
    else:
        _save_text(experiment, path if path.endswith(".txt") else path + ".txt")


def save_plot_dialog(parent: QWidget, plot_widget) -> None:
    """Open a file-save dialog and save the plot figure."""
    path, selected_filter = QFileDialog.getSaveFileName(
        parent,
        "Save Plot",
        os.path.expanduser("~"),
        "PDF (*.pdf);;PNG (*.png)",
    )
    if not path:
        return

    if not (path.endswith(".pdf") or path.endswith(".png")):
        ext = ".pdf" if "PDF" in selected_filter else ".png"
        path += ext

    plot_widget.save_plot(path)
    logger.info("Plot saved to %s", path)


def save_params_dialog(parent: QWidget, params: dict) -> None:
    path, _ = QFileDialog.getSaveFileName(
        parent,
        "Save Parameters",
        os.path.expanduser("~"),
        "YAML Parameter File (*.yml)",
    )
    if not path:
        return
    if not path.endswith(".yml"):
        path += ".yml"
    with open(path, "w") as f:
        yaml.dump(params, f)
    logger.info("Parameters saved to %s", path)


def load_params_dialog(parent: QWidget) -> dict | None:
    path, _ = QFileDialog.getOpenFileName(
        parent,
        "Load Parameters",
        os.path.expanduser("~"),
        "YAML Parameter File (*.yml)",
    )
    if not path:
        return None
    with open(path, "r") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _save_text(experiment, path: str):
    """Write all data channels as space-separated columns."""
    try:
        with open(path, "w") as f:
            for key, data in experiment.data.items():
                f.write("# {}\n".format(key))
                for scan_idx, scan in enumerate(data):
                    f.write("# scan {}\n".format(scan_idx))
                    rows = list(zip(*scan))
                    for row in rows:
                        f.write("\t".join(f"{v:.8g}" for v in row) + "\n")
        logger.info("Data saved to %s", path)
    except Exception as e:
        logger.error("Failed to save data: %s", e)


def _save_npy(experiment, path: str):
    try:
        arrays = {}
        for key, data in experiment.data.items():
            for scan_idx, scan in enumerate(data):
                arr_key = "{}_scan{}".format(key, scan_idx)
                arrays[arr_key] = np.array(scan)
        np.save(path, arrays, allow_pickle=True)
        logger.info("Data saved to %s", path)
    except Exception as e:
        logger.error("Failed to save data: %s", e)
