import struct
import time

from .experiment_template import PlotBox, Experiment


class LSVExp(Experiment):
    """Linear Scan Voltammetry experiment."""

    id = "lsv"

    def setup(self):
        self.plotlims["current_voltage"]["xlims"] = tuple(
            sorted((int(self.parameters["start"]), int(self.parameters["stop"])))
        )
        super().setup()

        self.datatype = "linearData"
        self.datalength = 2
        self.databytes = 6

        self.stop_mv = int(self.parameters["stop"])
        self.max_mv = abs(int(self.parameters["start"]) - int(self.parameters["stop"]))

        self.commands += ["E"]
        self.commands[2] += "L"
        self.commands[2] += str(self.parameters["clean_s"]) + " "
        self.commands[2] += str(self.parameters["dep_s"]) + " "
        self.commands[2] += self._precond_potential(self.parameters["clean_mV"]) + " "
        self.commands[2] += self._precond_potential(self.parameters["dep_mV"]) + " "
        self.commands[2] += self._sweep_value(self.parameters["start"]) + " "
        self.commands[2] += self._sweep_value(self.parameters["stop"]) + " "
        self.commands[2] += self._sweep_value(self.parameters["slope"], offset=False) + " "

    def get_progress(self) -> float:
        try:
            return 1 - (
                abs(self.stop_mv - self.data["current_voltage"][-1][0][-1]) / self.max_mv
            )
        except IndexError:
            return 0.0
