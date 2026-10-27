import multiprocessing as mp
import os
import queue
import time
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QSplitter

from dstat_interface.core.dstat import comm
from dstat_interface.core.interface import main_window
from dstat_interface.core.interface.main_window import MainWindow
from dstat_interface.core.interface.protocol_view import ProtocolView


class FakeSerial:
    """Minimal stand-in for serial.Serial used by SerialTrace tests."""

    is_open = True

    def __init__(self, replies=()):
        self.written = []
        self.closed = False
        self._replies = list(replies)

    def write(self, data):
        self.written.append(bytes(data))
        return len(data)

    def readline(self, *args, **kwargs):
        return self._replies.pop(0) if self._replies else b""

    def read(self, size=1):
        return b"\x00" * size

    def close(self):
        self.closed = True


def drain(queue_obj, timeout=2.0, idle=0.2):
    """Collect everything the queue feeder managed to publish."""
    entries = []
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return entries
        wait = remaining if not entries else min(idle, remaining)
        try:
            entries.append(queue_obj.get(timeout=wait))
        except queue.Empty:
            return entries


class SerialTraceTests(unittest.TestCase):
    def setUp(self):
        self.queue = mp.Queue()
        self.serial = FakeSerial([b"@ACK 5\r\n", b"@RCV 5\r\n", b"#firmware ready\r\n"])
        self.trace = comm.SerialTrace(self.serial, self.queue)

    def tearDown(self):
        self.queue.close()

    def test_writes_and_replies_are_traced_by_direction(self):
        self.trace.write(b"!5\n")
        self.trace.write("EA20 72 1 \n".encode())

        self.assertEqual(self.trace.readline(), b"@ACK 5\r\n")
        self.assertEqual(self.trace.readline(), b"@RCV 5\r\n")
        self.assertEqual(self.trace.readline(), b"#firmware ready\r\n")

        self.assertEqual(
            drain(self.queue),
            [
                ("tx", "!5"),
                ("tx", "EA20 72 1 "),
                ("rx", "@ACK 5"),
                ("rx", "@RCV 5"),
                ("info", "#firmware ready"),
            ],
        )

    def test_trailing_space_is_preserved_in_trace_text(self):
        self.trace.write(b"!0 ")
        self.assertEqual(drain(self.queue), [("tx", "!0 ")])

    def test_attributes_are_forwarded_to_the_real_port(self):
        self.trace.timeout = 2
        self.assertEqual(self.serial.timeout, 2)
        self.assertTrue(self.trace.is_open)

    def test_single_character_stop_command_is_forwarded(self):
        self.trace.write(b"a")
        self.assertEqual(self.serial.written[-1], b"a")
        self.assertEqual(drain(self.queue), [("tx", "a")])

    def test_data_frames_are_summarised_instead_of_traced(self):
        trace = comm.SerialTrace(FakeSerial(), self.queue)
        for _ in range(250):
            trace._ser._replies.append(b"B\r\n")
            trace.readline()

        entries = drain(self.queue)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0][0], "info")
        self.assertIn("200", entries[0][1])

    def test_notes_are_queued(self):
        self.trace.note(comm.TRACE_WARN, "expected @ACK 3, got '@ACK 9'")
        self.assertEqual(
            drain(self.queue),
            [("warn", "expected @ACK 3, got '@ACK 9'")],
        )


class SerialConnectionTraceTests(unittest.TestCase):
    def collect(self, connection, expected, timeout=2.0):
        """Poll get_trace() the way the GUI timer does until *expected* items."""
        entries = []
        deadline = time.monotonic() + timeout
        while len(entries) < expected and time.monotonic() < deadline:
            entries.extend(connection.get_trace())
            if len(entries) < expected:
                time.sleep(0.01)
        return entries

    def test_get_trace_drains_the_queue(self):
        connection = comm.SerialConnection()
        connection.trace_queue = mp.Queue()
        connection.trace_queue.put(("tx", "!1"))
        connection.trace_queue.put(("rx", "@ACK 1"))

        self.assertEqual(
            self.collect(connection, 2), [("tx", "!1"), ("rx", "@ACK 1")]
        )
        self.assertEqual(connection.get_trace(), [])

    def test_get_trace_honours_the_batch_limit(self):
        connection = comm.SerialConnection()
        connection.trace_queue = mp.Queue()
        for index in range(5):
            connection.trace_queue.put(("tx", "cmd{}".format(index)))

        batches = []
        deadline = time.monotonic() + 2.0
        while sum(len(b) for b in batches) < 5 and time.monotonic() < deadline:
            batches.append(connection.get_trace(limit=2))
            time.sleep(0.01)

        self.assertTrue(all(len(batch) <= 2 for batch in batches))
        self.assertEqual(sum(len(b) for b in batches), 5)

    def test_get_trace_without_a_connection_is_empty(self):
        self.assertEqual(comm.SerialConnection().get_trace(), [])


class ProtocolViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.view = ProtocolView()

    def tearDown(self):
        self.view.deleteLater()

    def test_entries_show_the_sent_text_with_its_trailing_space_marked(self):
        self.view.append("tx", "EA20 72 1 ")
        self.view.append("rx", "@ACK 11")

        text = self.view.plain_text()
        self.assertIn("EA20 72 1\u00b7", text)
        self.assertIn("@ACK 11", text)

    def test_directions_use_different_colours(self):
        self.view.append("tx", "!1")
        self.view.append("rx", "@ACK 1")

        html = self.view.text.document().toHtml().lower()
        self.assertIn("1565c0", html)
        self.assertIn("1b5e20", html)

    def test_unchecked_direction_is_filtered_out(self):
        self.view.check_rx.setChecked(False)
        self.view.append("rx", "@ACK 1")
        self.view.append("tx", "!1")

        text = self.view.plain_text()
        self.assertNotIn("@ACK 1", text)
        self.assertIn("!1", text)

    def test_clear_empties_the_log(self):
        self.view.append("tx", "!1")
        self.view.clear()
        self.assertEqual(self.view.plain_text(), "")


class MainWindowProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()

    def test_protocol_panel_is_the_right_hand_pane(self):
        root_layout = self.window.centralWidget().layout()
        splitter = root_layout.itemAt(0).widget()
        self.assertIsInstance(splitter, QSplitter)
        self.assertIs(splitter.widget(2), self.window.protocol_view)

    def test_trace_entries_from_the_worker_reach_the_panel(self):
        serial_connection = Mock(is_connected=True)
        serial_connection.get_trace.return_value = [
            ("tx", "!11"),
            ("rx", "@ACK 11"),
            ("warn", "expected @RCV 11, got '@ACK 3'"),
        ]

        with patch.object(main_window.state, "ser", serial_connection):
            self.window._poll_trace()

        text = self.window.protocol_view.plain_text()
        self.assertIn("!11", text)
        self.assertIn("@ACK 11", text)
        self.assertIn("expected @RCV 11", text)

    def test_view_menu_can_hide_and_restore_the_panel(self):
        self.window._toggle_protocol_panel(False)
        self.assertFalse(self.window.protocol_view.isVisibleTo(self.window))
        self.window._toggle_protocol_panel(True)
        self.assertTrue(self.window.protocol_view.isVisibleTo(self.window))


if __name__ == "__main__":
    unittest.main()
