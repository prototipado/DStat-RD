"""Gain-offset calibration experiment.

Port of the legacy ``CALExp``. Runs a single 0 mV chrono step for a given
gain and returns the average raw ADC code, which the calibration dialog turns
into a per-gain trim.
"""

import logging
import struct
import time

from .experiment_template import Experiment

logger = logging.getLogger(__name__)


class CalibExp(Experiment):
    id = "cal"

    def __init__(self, parameters: dict):
        self.parameters = parameters
        self.current_command = None
        self.databytes = 8
        self.datapoint = 0
        self.scan = 0
        self.time = []
        self.plots = []
        self.df = None

        from ..dstat import state
        self.re_voltage_scale = getattr(state.board_instance, "re_voltage_scale", 1) if state.board_instance else 1
        try:
            self.gain = state.board_instance.gain[int(self.parameters["gain"])]
        except Exception:
            self.gain = 1
        try:
            self.gain_trim = int(
                state.settings[
                    state.board_instance.gain_trim[int(self.parameters["gain"])]
                ][1]
            )
        except Exception:
            self.gain_trim = 0

        self.commands = []
        self._samples: list[int] = []
        self.setup()

    def setup(self):
        self.datatype = "linearData"
        self.datalength = 2
        self.databytes = 8
        self.data = {"current_time": [([], [])]}
        self.columns = ["Time (s)", "Current (A)"]

        gain_idx = int(self.parameters.get("gain", 0))
        time_s = int(self.parameters.get("time", 10))
        self.commands = [
            "EA2 3 1 ",
            "EG{} 0 ".format(gain_idx),
            ("ER1 0 ", [32768, time_s]),
        ]

    def data_handler(self, data_input):
        scan, data = data_input
        seconds, milliseconds, current = struct.unpack("<HHl", data)
        self._samples.append(int(current))
        return (scan, (seconds + milliseconds / 1000.0, current))

    def serial_handler(self) -> bool:
        # Reuse base implementation but send the averaged offset at @DONE.
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
                        self.data_handler((scan, raw))
                        self.datapoint += 1

                    elif line.lstrip().startswith("S"):
                        scan += 1

                    elif line.lstrip().startswith("#"):
                        logger.info(line.lstrip())

                    elif line.lstrip().startswith("@DONE"):
                        # Average (skip first sample) and send offset.
                        samples = self._samples[1:] if len(self._samples) > 1 else self._samples
                        if samples:
                            total = sum(samples)
                            avg = int(total / len(samples))
                            # Clamp to int16 range.
                            avg = max(-32768, min(32767, avg))
                        else:
                            avg = 0
                        try:
                            self.data_pipe.send(avg)
                        except Exception:
                            pass
                        time.sleep(0.8)
                        # Drain trailing device->PC bytes (fixed budget).
                        try:
                            end = time.monotonic() + 2.0
                            while time.monotonic() < end:
                                n = getattr(self.serial, "in_waiting", 0)
                                if n:
                                    self.serial.read(n)
                                time.sleep(0.1)
                        except Exception:
                            pass
                        return True

        except Exception as exc:
            logger.exception("CalibExp serial error: %s", exc)
            raise

    def store_data(self, incoming, newline: bool):
        pass

    def get_progress(self) -> float:
        return 0.0

    def data_postprocessing(self, data):
        return None

    def experiment_done(self):
        pass

    def data_to_pandas(self):
        pass
