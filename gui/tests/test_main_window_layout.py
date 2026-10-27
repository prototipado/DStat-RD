import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QGroupBox, QSplitter, QTabWidget

from dstat_interface.core.interface import main_window
from dstat_interface.core.interface.main_window import MainWindow


class MainWindowLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()

    def tearDown(self):
        self.window.close()

    def test_classic_left_right_and_bottom_regions_are_kept(self):
        root_layout = self.window.centralWidget().layout()
        splitter = root_layout.itemAt(0).widget()
        comm_group = root_layout.itemAt(1).widget()

        self.assertIsInstance(splitter, QSplitter)
        self.assertIsInstance(comm_group, QGroupBox)
        self.assertEqual(comm_group.title(), "Communications")

        right_layout = splitter.widget(1).layout()
        self.assertEqual(right_layout.itemAt(0).widget().title(), "Autosave")
        self.assertIsInstance(right_layout.itemAt(1).widget(), QTabWidget)

    def test_tabs_and_connection_controls_remain_available(self):
        self.assertEqual(
            [self.window.tabs.tabText(i) for i in range(self.window.tabs.count())],
            ["Plot", "Raw Data", "Info"],
        )
        self.assertEqual(self.window.btn_refresh.text(), "Refresh")
        self.assertEqual(self.window.btn_connect.text(), "Connect")
        self.assertEqual(self.window.windowTitle().split("  v")[0], "DStat GUI 2.1")

    def test_closed_serial_pipe_while_resuming_ocp_does_not_escape_qt_slot(self):
        serial_connection = Mock(is_connected=True)
        serial_connection.flush_data.side_effect = BrokenPipeError("serial worker exited")

        with patch.object(main_window.state, "ser", serial_connection):
            with patch.object(main_window.comm, "supports_ocp", return_value=True):
                self.window._start_ocp()

        self.assertIn("OCP readout could not resume", self.window.status_bar.currentMessage())
        self.assertFalse(self.window._ocp_running)

    def test_serial_error_disconnects_without_restarting_ocp(self):
        serial_connection = Mock(is_connected=True)
        loop = Mock(serial_error=True)
        self.window.current_loop = loop

        with patch.object(main_window.state, "ser", serial_connection):
            with patch.object(self.window, "_update_plot"):
                with patch.object(self.window, "_populate_data_view"):
                    with patch.object(self.window, "_start_ocp") as start_ocp:
                        self.window._on_experiment_done()

        serial_connection.disconnect_serial.assert_called_once_with()
        start_ocp.assert_not_called()
        self.assertIn("Reconnect to continue", self.window.status_bar.currentMessage())

    def test_shutdown_stops_timers_and_closes_serial_connection(self):
        serial_connection = Mock(is_connected=True)
        loop = Mock()
        self.window.current_loop = loop

        with patch.object(main_window.state, "ser", serial_connection):
            self.window._shutdown_serial_connection()

        loop._stop_timers.assert_called_once_with()
        serial_connection.disconnect_serial.assert_called_once_with()

    def test_lost_pipe_while_stopping_ocp_is_handled_before_execute(self):
        serial_connection = Mock(is_connected=True)
        serial_connection.send_ctrl.side_effect = main_window.comm.ConnectionError(
            "Serial control pipe is no longer available."
        )

        with patch.object(main_window.state, "ser", serial_connection):
            self.window._ocp_running = True
            stopped = self.window._stop_ocp()

        self.assertFalse(stopped)
        serial_connection.disconnect_serial.assert_called_once_with()
        self.assertIn("Reconnect before continuing", self.window.status_bar.currentMessage())

    def test_worker_disconnect_message_during_ocp_resets_connection(self):
        serial_connection = Mock(is_connected=True)
        serial_connection.get_proc.return_value = None
        serial_connection.get_data.return_value = "DISCONNECT"

        with patch.object(main_window.state, "ser", serial_connection):
            self.window._ocp_running = True
            self.window._poll_ocp()

        serial_connection.disconnect_serial.assert_called_once_with()
        self.assertFalse(self.window._ocp_running)


if __name__ == "__main__":
    unittest.main()
