#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DStat Interface – Python 3 / Qt6 entry point.

Run with:
    python -m dstat_interface.main
or:
    python dstat_interface/main.py
"""

import sys
import os
import logging
import multiprocessing
import faulthandler
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Ensure the project root (parent of dstat_interface/) is on sys.path so that
# "dstat_interface" is importable regardless of how this script is invoked.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Required on Windows so that spawned subprocesses don't re-run this module.
multiprocessing.freeze_support()

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _configure_diagnostics():
    log_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "DStat GUI 2.0" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "dstat-gui.log"

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    ))
    logging.getLogger().addHandler(file_handler)

    crash_file = open(log_dir / "crash.log", "a", encoding="utf-8")
    faulthandler.enable(file=crash_file)
    return crash_file


def _log_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        return
    logger.critical(
        "Unhandled application exception",
        exc_info=(exc_type, exc_value, exc_traceback),
    )


# ---------------------------------------------------------------------------
# Qt application
# ---------------------------------------------------------------------------

def main():
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from dstat_interface.core.interface.main_window import MainWindow

    crash_file = _configure_diagnostics()
    sys.excepthook = _log_unhandled_exception
    app = QApplication(sys.argv)
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    app.setApplicationName("DStat GUI 2.1")
    app.setOrganizationName("Wheeler Microfluidics Laboratory")

    # Apply persisted theme before building the window.
    from dstat_interface.core.interface.theme_manager import apply_theme
    apply_theme(app)

    window = MainWindow()
    app.aboutToQuit.connect(window._shutdown_serial_connection)
    window.show()

    try:
        sys.exit(app.exec())
    finally:
        faulthandler.disable()
        crash_file.close()


if __name__ == "__main__":
    main()
