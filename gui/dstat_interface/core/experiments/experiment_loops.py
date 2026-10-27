"""Experiment polling loops.

Replaces the GTK `GObject.idle_add` / `GObject.timeout_add` machinery with
Qt `QTimer` objects so the main Qt event loop can drive data acquisition.
"""

import logging

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from ..dstat import state

logger = logging.getLogger(__name__)


class BaseLoop(QObject):
    """Poll the serial subprocess for data and process-status messages."""

    experiment_done = pyqtSignal()
    completion_error = pyqtSignal(str)
    progress_update = pyqtSignal(float)

    def __init__(self, experiment, callbacks: dict = None, parent=None):
        super().__init__(parent)
        self.current_exp = experiment
        self.line = None
        self.lastdataline = 0
        self._timers = []
        self._finished = False
        self.serial_error = False

        if callbacks:
            for signal_name, cb in callbacks.items():
                try:
                    getattr(self, signal_name).connect(cb)
                except AttributeError:
                    logger.warning("Invalid signal: %s", signal_name)

    def run(self):
        data_timer = QTimer(self)
        data_timer.timeout.connect(self._poll_data)
        data_timer.start(0)  # run as fast as possible

        proc_timer = QTimer(self)
        proc_timer.timeout.connect(self._poll_proc)
        proc_timer.start(20)

        progress_timer = QTimer(self)
        progress_timer.timeout.connect(self._update_progress)
        progress_timer.start(100)

        self._timers = [data_timer, proc_timer, progress_timer]

    def _stop_timers(self):
        for t in self._timers:
            t.stop()
        self._timers.clear()

    # ------------------------------------------------------------------

    def _poll_data(self):
        try:
            incoming = state.ser.get_data()
            while incoming is not None:
                try:
                    self.line = incoming[0]
                    if self.line > self.lastdataline:
                        newline = True
                        try:
                            self.current_exp.scan_process(self.lastdataline)
                        except AttributeError:
                            pass
                        self.lastdataline = self.line
                    else:
                        newline = False
                    self.current_exp.store_data(incoming, newline)
                except TypeError:
                    pass
                incoming = state.ser.get_data()

        except (EOFError, IOError) as err:
            logger.error("Data poll error: %s", err)
            self._finish()

    def _poll_proc(self):
        try:
            proc_buffer = state.ser.get_proc()
            if proc_buffer is not None:
                if proc_buffer in ("DONE", "SERIAL_ERROR", "ABORT"):
                    self._finish(serial_error=(proc_buffer == "SERIAL_ERROR"))
                else:
                    logger.warning("Unrecognised return code: %s", proc_buffer)

        except (EOFError, IOError) as err:
            logger.warning("Proc poll error: %s", err)
            self._finish()

    def _update_progress(self):
        try:
            self.progress_update.emit(self.current_exp.get_progress())
        except Exception:
            pass

    def _finish(self, serial_error: bool = False):
        if self._finished:
            return
        self._finished = True
        self.serial_error = serial_error
        self._stop_timers()

        if serial_error:
            logger.error("Serial error during experiment.")

        errors = []
        for finalize in (
            lambda: self.current_exp.scan_process(self.lastdataline),
            self.current_exp.experiment_done,
        ):
            try:
                finalize()
            except Exception as exc:
                logger.exception("Experiment finalization failed")
                errors.append(str(exc))

        self.experiment_done.emit()
        if errors:
            self.completion_error.emit("; ".join(errors))


# Alias so existing subclasses that reference PlotLoop still work
PlotLoop = BaseLoop
