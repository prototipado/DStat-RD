import struct
import time
from copy import deepcopy

from .experiment_template import PlotBox, Experiment


class SWVBox(PlotBox):
    def setup(self):
        self.plot_format = {
            "swv": {
                "xlabel": "Voltage (mV)",
                "ylabel": "Current (A)",
            }
        }


class SWVExp(Experiment):
    """Square Wave Voltammetry experiment."""

    id = "swv"

    def setup(self):
        self.datatype = "SWVData"
        self.xlabel = "Voltage (mV)"
        self.ylabel = "Current (A)"
        self.data = {"swv": [([], [], [], [])]}  # voltage, net, forward, reverse
        self.line_data = ([], [], [], [])
        self.datalength = 2 * int(self.parameters["scans"])
        self.databytes = 10
        self.columns = [
            "Voltage (mV)",
            "Net Current (A)",
            "Forward Current (A)",
            "Reverse Current (A)",
        ]
        self.plotlims = {
            "swv": {
                "xlims": tuple(
                    sorted(
                        (int(self.parameters["start"]), int(self.parameters["stop"]))
                    )
                )
            }
        }

        plot = SWVBox()
        plot.setlims("swv", **self.plotlims["swv"])
        self.plots.append(plot)

        self.stop_mv = int(self.parameters["stop"])
        self.max_mv = abs(int(self.parameters["start"]) - int(self.parameters["stop"]))
        self.scan_points = self.max_mv * 2 / float(self.parameters["step"])

        self.commands += ["E"]
        self.commands[2] += "S"
        self.commands[2] += str(self.parameters["clean_s"]) + " "
        self.commands[2] += str(self.parameters["dep_s"]) + " "
        self.commands[2] += self._precond_potential(self.parameters["clean_mV"]) + " "
        self.commands[2] += self._precond_potential(self.parameters["dep_mV"]) + " "
        self.commands[2] += self._sweep_value(self.parameters["start"]) + " "
        self.commands[2] += self._sweep_value(self.parameters["stop"]) + " "
        self.commands[2] += self._sweep_value(self.parameters["step"], offset=False) + " "
        self.commands[2] += self._sweep_value(self.parameters["pulse"], offset=False) + " "
        self.commands[2] += str(self.parameters["freq"]) + " "
        self.commands[2] += str(self.parameters["scans"]) + " "

    def data_handler(self, data_input):
        scan, data = data_input
        # firmware sends {uint16_t lastindex; int32_t forward; int32_t reverse;}
        # -> 10 bytes, see experiment.c in the firmware.
        voltage, forward, reverse = struct.unpack("<Hll", data)
        f_trim = forward + self.gain_trim
        r_trim = reverse + self.gain_trim
        scale = 1.5 / self.gain / 8388607
        return (
            scan,
            (
                (voltage - 32768) * (3000.0 / 65536) * self.re_voltage_scale,
                (f_trim - r_trim) * scale,
                f_trim * scale,
                r_trim * scale,
            ),
        )

    def store_data(self, incoming, newline: bool):
        line, data = incoming
        if newline:
            self.data["swv"].append(deepcopy(self.line_data))
        for i, item in enumerate(self.data["swv"][line]):
            item.append(data[i])

    def get_progress(self) -> float:
        try:
            scans = int(self.parameters["scans"])
            if scans != 0:
                scans_prog = (len(self.data["swv"]) - 1) / float(scans)
                scan_prog = (
                    (len(self.data["swv"][-1][0]) - 1) / self.scan_points / float(scans)
                )
                return min(scans_prog + scan_prog, 1.0)
            return 1 - (
                abs(self.stop_mv - self.data["swv"][-1][0][-1]) / self.max_mv
            )
        except (IndexError, ZeroDivisionError):
            return 0.0
