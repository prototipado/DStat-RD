import os
import unittest
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from dstat_interface.core.experiments.experiment_loops import BaseLoop
from dstat_interface.core.experiments.experiment_template import Experiment


class ExperimentCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_finalization_error_is_reported_without_skipping_completion(self):
        experiment = Mock()
        experiment.experiment_done.side_effect = ValueError("invalid final data")
        loop = BaseLoop(experiment)
        completed = []
        errors = []
        loop.experiment_done.connect(lambda: completed.append(True))
        loop.completion_error.connect(errors.append)

        loop._finish()
        loop._finish()

        experiment.scan_process.assert_called_once_with(0)
        experiment.experiment_done.assert_called_once_with()
        self.assertEqual(completed, [True])
        self.assertEqual(errors, ["invalid final data"])

    def test_scan_finalization_error_does_not_prevent_data_finalization(self):
        experiment = Mock()
        experiment.scan_process.side_effect = RuntimeError("invalid final scan")
        loop = BaseLoop(experiment)
        errors = []
        loop.completion_error.connect(errors.append)

        loop._finish()

        experiment.experiment_done.assert_called_once_with()
        self.assertEqual(errors, ["invalid final scan"])

    def test_serial_error_is_preserved_when_finalizing_experiment(self):
        experiment = Mock()
        loop = BaseLoop(experiment)
        completed = []
        loop.experiment_done.connect(lambda: completed.append(True))

        loop._finish(serial_error=True)

        self.assertTrue(loop.serial_error)
        self.assertEqual(completed, [True])

    def test_data_to_pandas_uses_experiment_columns_without_plot_format(self):
        experiment = Experiment.__new__(Experiment)
        experiment.data = {"voltage_time": [([0.0, 1.0], [0.2, 0.3])]}
        experiment.columns = ["Time (s)", "Voltage (V)"]

        experiment.data_to_pandas()

        frame = experiment.df["voltage_time"]
        self.assertEqual(
            list(frame.columns),
            ["Scan", "Time (s)", "Voltage (V)"],
        )
        self.assertEqual(frame["Voltage (V)"].tolist(), [0.2, 0.3])


if __name__ == "__main__":
    unittest.main()
