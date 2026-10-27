import struct
import time

from .experiment_template import PlotBox, Experiment


class CVExp(Experiment):
    """Cyclic Voltammetry experiment."""

    id = "cve"

    def setup(self):
        self.plotlims["current_voltage"]["xlims"] = tuple(
            sorted((int(self.parameters["v1"]), int(self.parameters["v2"])))
        )
        super().setup()

        self.datatype = "CVData"
        self.xlabel = "Voltage (mV)"
        self.ylabel = "Current (A)"
        self.datalength = 2 * int(self.parameters["scans"])
        self.databytes = 6  # uint16 + int32

        self.commands += ["E"]
        self.commands[2] += "C"
        self.commands[2] += str(self.parameters["clean_s"]) + " "
        self.commands[2] += str(self.parameters["dep_s"]) + " "
        self.commands[2] += self._precond_potential(self.parameters["clean_mV"]) + " "
        self.commands[2] += self._precond_potential(self.parameters["dep_mV"]) + " "
        self.commands[2] += self._sweep_value(self.parameters["v1"]) + " "
        self.commands[2] += self._sweep_value(self.parameters["v2"]) + " "
        self.commands[2] += self._sweep_value(self.parameters["start"]) + " "
        self.commands[2] += str(self.parameters["scans"]) + " "
        self.commands[2] += self._sweep_value(self.parameters["slope"], offset=False) + " "

    def get_progress(self) -> float:
        return (len(self.data["current_voltage"]) - 1) / float(self.parameters["scans"])
