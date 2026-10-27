import struct
import time
from copy import deepcopy

from .experiment_template import PlotBox, Experiment


class PotBox(PlotBox):
    def setup(self):
        self.plot_format = {
            "voltage_time": {
                "xlabel": "Time (s)",
                "ylabel": "Voltage (V)",
            }
        }


class PotExp(Experiment):
    """Potentiometry experiment."""

    id = "pot"

    def setup(self):
        self.datatype = "linearData"
        self.datalength = 2
        self.databytes = 8
        self.data = {"voltage_time": [([], [])]}
        self.columns = ["Time (s)", "Voltage (V)"]
        self.total_time = int(self.parameters["time"])
        self.plotlims = {"voltage_time": {"xlims": (0, self.total_time)}}

        self.commands += ["E"]
        self.commands[2] += "P"
        self.commands[2] += str(self.parameters["time"]) + " 1 "

        plot = PotBox(["voltage_time"])
        plot.setlims("voltage_time", **self.plotlims["voltage_time"])
        self.plots.append(plot)

    def data_handler(self, data_input):
        scan, data = data_input
        seconds, milliseconds, voltage = struct.unpack("<HHl", data)
        return (
            scan,
            (
                seconds + milliseconds / 1000.0,
                voltage * self.re_voltage_scale * (1.5 / 8388607.0),
            ),
        )

    def store_data(self, incoming, newline: bool):
        line, data = incoming
        if newline:
            self.data["voltage_time"].append(deepcopy(([], [])))
        for i, item in enumerate(self.data["voltage_time"][line]):
            item.append(data[i])

    def get_progress(self) -> float:
        try:
            return self.data["voltage_time"][-1][0][-1] / self.total_time
        except IndexError:
            return 0.0
