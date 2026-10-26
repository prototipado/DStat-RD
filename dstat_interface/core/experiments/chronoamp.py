import struct
import time
from copy import deepcopy

import numpy as np

from .experiment_template import PlotBox, Experiment, exp_logger


class ChronoampBox(PlotBox):
    def setup(self):
        self.plot_format = {
            "current_time": {
                "xlabel": "Time (s)",
                "ylabel": "Current (A)",
            }
        }


class Chronoamp(Experiment):
    """Chronoamperometry experiment."""

    id = "cae"

    def setup(self):
        self.datatype = "linearData"
        self.datalength = 2
        self.databytes = 8
        self.data = {"current_time": [([], [])]}
        self.columns = ["Time (s)", "Current (A)"]
        self.total_time = sum(self.parameters["time"])
        self.plotlims = {"current_time": {"xlims": (0, self.total_time)}}

        self.commands.append(
            ("ER{} 0 ".format(len(self.parameters["potential"])), [])
        )
        for i in self.parameters["potential"]:
            self.commands[-1][1].append(str(int(i * (65536.0 / 3000) + 32768)))
        for i in self.parameters["time"]:
            self.commands[-1][1].append(str(i))

        plot = ChronoampBox(["current_time"])
        plot.setlims("current_time", **self.plotlims["current_time"])
        self.plots.append(plot)

    def data_handler(self, data_input):
        scan, data = data_input
        seconds, milliseconds, current = struct.unpack("<HHl", data)
        return (
            scan,
            (
                seconds + milliseconds / 1000.0,
                (current + self.gain_trim) * (1.5 / self.gain / 8388607),
            ),
        )

    def store_data(self, incoming, newline: bool):
        line, data = incoming
        if newline:
            self.data["current_time"].append(deepcopy(([], [])))
        for i, item in enumerate(self.data["current_time"][line]):
            item.append(data[i])

    def get_progress(self) -> float:
        try:
            return self.data["current_time"][-1][0][-1] / self.total_time
        except IndexError:
            return 0.0
