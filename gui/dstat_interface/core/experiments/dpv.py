import struct
from copy import deepcopy

from .swv import SWVBox, SWVExp


class DPVExp(SWVExp):
    """Differential Pulse Voltammetry experiment.

    DPV shares SWV's 10-byte datapoint layout (uint16 voltage + int32 forward
    + int32 reverse current) but is triggered with 'ED' and is driven by a
    *period*/*width* pulse pair instead of a frequency and scan count.
    """

    id = "dpv"

    def setup(self):
        self.datatype = "SWVData"
        self.xlabel = "Voltage (mV)"
        self.ylabel = "Current (A)"
        self.data = {"swv": [([], [], [], [])]}  # voltage, net, forward, reverse
        self.line_data = ([], [], [], [])
        # The firmware runs a single differential-pulse sweep.
        self.datalength = 2
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

        self.commands += ["E"]
        self.commands[2] += "D"
        self.commands[2] += str(self.parameters["clean_s"]) + " "
        self.commands[2] += str(self.parameters["dep_s"]) + " "
        self.commands[2] += self._precond_potential(self.parameters["clean_mV"]) + " "
        self.commands[2] += self._precond_potential(self.parameters["dep_mV"]) + " "
        self.commands[2] += self._sweep_value(self.parameters["start"]) + " "
        self.commands[2] += self._sweep_value(self.parameters["stop"]) + " "
        self.commands[2] += self._sweep_value(self.parameters["step"], offset=False) + " "
        self.commands[2] += self._sweep_value(self.parameters["pulse"], offset=False) + " "
        self.commands[2] += str(self.parameters["period"]) + " "
        self.commands[2] += str(self.parameters["width"]) + " "

    def get_progress(self) -> float:
        try:
            return 1 - (
                abs(self.stop_mv - self.data["swv"][-1][0][-1]) / self.max_mv
            )
        except (IndexError, ZeroDivisionError):
            return 0.0