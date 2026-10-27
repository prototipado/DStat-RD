"""Base experiment class.

All concrete experiment types inherit from `Experiment`.  The `run()` method
is called inside the serial subprocess (just as in the original GTK version)
and communicates with the main process through the pipe objects passed to it.

`PlotBox` is a lightweight matplotlib figure container that is serialisable
(can be sent across the mp.Pipe) but does NOT hold any Qt widgets – those are
created on the main-process side in `plot_widget.py`.
"""

import logging
import struct
import time
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime
from math import ceil

import serial
import numpy as np
from pandas import DataFrame, concat

from ..dstat import state
from ..dstat.comm import TransmitError, TRACE_WARN, TRACE_ERROR, _trace_note

logger = logging.getLogger(__name__)
dstat_logger = logging.getLogger("{}.DSTAT".format(__name__))
exp_logger = logging.getLogger("{}.Experiment".format(__name__))

# MAX5443 DAC resolution and bipolar full-scale range.
DAC_OFFSET = 32768
DAC_FULL_SCALE_MV = 3000.0


# ---------------------------------------------------------------------------
# PlotBox – pure data container for plot limits / format, no Qt inside
# ---------------------------------------------------------------------------

class PlotBox:
    """Stores the format spec for a single matplotlib axes set.

    Subclass and override :meth:`setup` and :meth:`format_plots` to customise
    axis labels and tick formats.  The actual ``matplotlib.figure.Figure`` is
    NOT created here; it lives in the Qt plot widget on the main thread.
    """

    def __init__(self, plot_keys=None):
        self.plot_keys = plot_keys or []
        self.plot_format = {}
        self._lims = {}
        self.setup()

    def setup(self):
        self.plot_format = {
            "current_voltage": {
                "xlabel": "Voltage (mV)",
                "ylabel": "Current (A)",
            }
        }

    def setlims(self, key, xlims=(0, 1), ylims=None):
        self._lims[key] = {"xlims": xlims, "ylims": ylims}

    def get_lims(self, key):
        return self._lims.get(key, {})


# ---------------------------------------------------------------------------
# Experiment base class
# ---------------------------------------------------------------------------

class Experiment:
    """Store and acquire a potentiostat experiment.

    Subclass and override :meth:`setup` to configure commands and data
    structures for a specific technique.  :meth:`run` is called in the serial
    subprocess.
    """

    id = None

    def __init__(self, parameters: dict):
        self.parameters = parameters
        self.current_command = None
        self.databytes = 8
        self.datapoint = 0
        self.scan = 0
        self.time = [datetime.utcnow()]
        self.plots = []
        self.df = None

        self.re_voltage_scale = state.board_instance.re_voltage_scale
        self.gain = state.board_instance.gain[int(self.parameters["gain"])]

        try:
            self.gain_trim = int(
                state.settings[
                    state.board_instance.gain_trim[int(self.parameters["gain"])]
                ][1]
            )
        except (AttributeError, KeyError, TypeError):
            self.gain_trim = 0
            logger.debug("No gain trim table.")

        self.commands = ["EA", "EG"]

        if self.parameters.get("buffer_true"):
            self.commands[0] += "2"
        else:
            self.commands[0] += "0"

        self.commands[0] += " {p[adc_rate]} {p[adc_pga]} ".format(p=self.parameters)
        self.commands[1] += "{p[gain]} {p[short_true]:d} ".format(p=self.parameters)

        self.plotlims = {"current_voltage": {"xlims": (0, 1)}}
        self.setup()
        self.time = [datetime.utcnow()]

    def setup(self):
        self.data = OrderedDict(current_voltage=[([], [])])
        self.columns = ["Voltage (mV)", "Current (A)"]
        self.line_data = ([], [])
        self.datatype = "CVData"
        self.xlabel = "Voltage (mV)"
        self.ylabel = "Current (A)"

        plot = PlotBox(["current_voltage"])
        plot.setlims("current_voltage", **self.plotlims["current_voltage"])
        self.plots.append(plot)

    # ------------------------------------------------------------------
    # Potential encoding
    #
    # The firmware only performs the mV -> DAC conversion itself when
    # dac_units_true is 0, which is the default (SETTINGS_DAC_UNITS_TRUE).
    # With dac_units_true = 1 the host must send DAC indexes instead.
    # Pre-conditioning potentials are always passed straight to precond(),
    # which expects a DAC index, so they are always converted here.
    # ------------------------------------------------------------------

    @property
    def dac_units_true(self) -> bool:
        """True when the DStat expects DAC indexes instead of mV."""
        try:
            return bool(int(state.settings["dac_units_true"][1]))
        except (KeyError, IndexError, TypeError, ValueError):
            return False

    def _mv_to_dac(self, mv, offset: bool = True) -> int:
        """Convert millivolts to a MAX5443 DAC index."""
        dac = float(mv) / self.re_voltage_scale * (65536.0 / DAC_FULL_SCALE_MV)
        return int(dac + DAC_OFFSET) if offset else int(dac)

    def _precond_potential(self, mv) -> str:
        """Encode a pre-conditioning potential (always a DAC index)."""
        return str(self._mv_to_dac(mv, offset=True))

    def _sweep_value(self, mv, offset: bool = True) -> str:
        """Encode a sweep potential / slope / step / pulse for the firmware."""
        if self.dac_units_true:
            return str(self._mv_to_dac(mv, offset=offset))
        return str(int(float(mv)))

    # ------------------------------------------------------------------
    # Serial write helpers (run in subprocess)
    # ------------------------------------------------------------------

    def write_command(self, cmd: str, params=None, retry: int = 5) -> bool:
        """Write a command string to the DStat and wait for ACK/RCV."""

        def get_reply(retries=3):
            while True:
                reply = self.serial.readline().rstrip().decode(errors="replace")
                if reply.startswith("#"):
                    dstat_logger.info(reply)
                elif reply == "":
                    retries -= 1
                    if retries <= 0:
                        raise TransmitError
                else:
                    return reply

        n = len(cmd)
        n_params = len(params) if params is not None else 0

        for _ in range(retry):
            tries = 5
            while True:
                time.sleep(0.2)
                self.serial.reset_input_buffer()
                self.serial.write("!{}\n".format(n).encode())
                time.sleep(0.1)
                try:
                    reply = get_reply()
                except TransmitError:
                    tries -= 1
                    if tries <= 0:
                        continue
                    continue
                else:
                    break

            if reply != "@ACK {}".format(n):
                logger.warning("Expected ACK got: %s", reply)
                _trace_note(
                    self.serial, TRACE_WARN,
                    "expected @ACK {}, got {!r}".format(n, reply),
                )
                continue

            tries = 5
            while True:
                self.serial.write("{}\n".format(cmd).encode())
                try:
                    reply = get_reply()
                except TransmitError:
                    tries -= 1
                    if tries <= 0:
                        continue
                    continue
                else:
                    break

            if reply != "@RCV {}".format(n):
                logger.warning("Expected RCV got: %s", reply)
                _trace_note(
                    self.serial, TRACE_WARN,
                    "expected @RCV {}, got {!r}".format(n, reply),
                )
                continue

            if params is None:
                return True

            tries = 5
            while True:
                try:
                    reply = get_reply()
                except TransmitError:
                    tries -= 1
                    if tries <= 0:
                        break
                    continue
                else:
                    break

            if reply != "@RQP {}".format(n_params):
                logger.warning("Expected RQP got: %s", reply)
                _trace_note(
                    self.serial, TRACE_WARN,
                    "expected @RQP {}, got {!r}".format(n_params, reply),
                )
                continue

            for i in params:
                tries = 5
                while True:
                    self.serial.write("{} ".format(i).encode())
                    try:
                        reply = get_reply()
                        if reply == "@RCVC {}".format(i):
                            break
                    except TransmitError:
                        tries -= 1
                        if tries <= 0:
                            continue
                        continue
                    else:
                        break
            return True
        _trace_note(
            self.serial, TRACE_ERROR,
            "command not delivered: {!r}".format(cmd),
        )
        return False

    # ------------------------------------------------------------------
    # Main run loop (executes in serial subprocess)
    # ------------------------------------------------------------------

    def run(self, ser, ctrl_pipe, data_pipe):
        """Execute experiment in the serial subprocess."""
        self.serial = ser
        self.ctrl_pipe = ctrl_pipe
        self.data_pipe = data_pipe

        exp_logger.info("Experiment running")
        status = "DONE"

        try:
            for i in self.commands:
                self.current_command = i
                if isinstance(i, str):
                    logger.info("Command: %s", i)
                    if not self.write_command(i):
                        status = "ABORT"
                        break
                else:
                    cmd, data = i[0], i[1]
                    logger.info("Command: %s", cmd)
                    if not self.write_command(cmd, params=data):
                        status = "ABORT"
                        break

                if not self.serial_handler():
                    status = (
                        "DISCONNECT"
                        if getattr(self, "disconnect_requested", False)
                        else "ABORT"
                    )
                    break

                time.sleep(0.5)

        except serial.SerialException:
            logger.exception(
                "Serial communication failed while running command %s",
                self.current_command,
            )
            status = "SERIAL_ERROR"
        finally:
            while self.ctrl_pipe.poll():
                self.ctrl_pipe.recv()

        return status

    def serial_handler(self) -> bool:
        """Handle binary data stream from DStat. Returns False on abort."""
        scan = 0

        def check_ctrl():
            if self.ctrl_pipe.poll():
                inp = self.ctrl_pipe.recv()
                if inp == "DISCONNECT":
                    self.serial.write(b"a")
                    self.serial.reset_input_buffer()
                    time.sleep(0.3)
                    self.disconnect_requested = True
                    return False
                elif inp == "a":
                    self.serial.write(b"a")
                else:
                    self.serial.write(inp.encode() if isinstance(inp, str) else inp)
            return True

        try:
            while True:
                if not check_ctrl():
                    return False
                for line in self.serial:
                    if not check_ctrl():
                        return False
                    line = line.rstrip().decode(errors="replace")

                    if line.startswith("B"):
                        raw = self.serial.read(size=self.databytes)
                        data = self.data_handler((scan, raw))
                        data = self.data_postprocessing(data)
                        if data is not None:
                            self.data_pipe.send(data)
                        self.datapoint += 1

                    elif line.lstrip().startswith("S"):
                        scan += 1

                    elif line.lstrip().startswith("#"):
                        dstat_logger.info(line.lstrip())

                    elif line.lstrip().startswith("@DONE"):
                        dstat_logger.debug(line.lstrip())
                        time.sleep(0.3)
                        return True

        except serial.SerialException:
            logger.exception(
                "Serial communication failed while reading command %s",
                self.current_command,
            )
            raise

    # ------------------------------------------------------------------
    # Data handling (main process side)
    # ------------------------------------------------------------------

    def data_handler(self, data_input):
        """Unpack raw bytes into (scan, (voltage_mV, current_A))."""
        scan, data = data_input
        voltage, current = struct.unpack("<Hl", data)  # uint16 + int32
        return (
            scan,
            (
                (voltage - 32768) * (3000.0 / 65536) * self.re_voltage_scale,
                (current + self.gain_trim) * (1.5 / 8388607) / self.gain,
            ),
        )

    def data_postprocessing(self, data):
        """Discard the first datapoint (usually glitched)."""
        if self.datapoint <= 1:
            return None
        return data

    def store_data(self, incoming, newline: bool):
        """Store incoming data tuple into self.data."""
        line, data = incoming
        if newline:
            self.data["current_voltage"].append(deepcopy(self.line_data))
        for i, item in enumerate(self.data["current_voltage"][line]):
            item.append(data[i])

    def scan_process(self, line):
        pass

    def experiment_done(self):
        self.data_to_pandas()
        self.time.append(datetime.utcnow())

    def get_progress(self) -> float:
        return 0.0

    # ------------------------------------------------------------------
    # Pandas export
    # ------------------------------------------------------------------

    def data_to_pandas(self):
        self.df = OrderedDict()
        for name, data in self.data.items():
            labels = list(self.columns)
            if not labels:
                continue
            frames = []
            for n, line in enumerate(data):
                if len(line) != len(labels):
                    continue
                frames.append(
                    DataFrame(
                        OrderedDict(zip(["Scan"] + labels, [n] + list(line)))
                    )
                )
            if frames:
                self.df[name] = concat(frames, ignore_index=True)
