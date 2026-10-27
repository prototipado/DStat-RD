import unittest
from unittest.mock import Mock, patch

import serial

from dstat_interface.core.dstat import comm
from dstat_interface.core.experiments.experiment_template import Experiment


class SerialProcessTests(unittest.TestCase):
    def test_parent_closes_worker_pipe_endpoints_after_process_start(self):
        connection = comm.SerialConnection()
        pipe_ends = [Mock() for _ in range(6)]
        process = Mock()
        process.is_alive.return_value = True
        pipe_ends[0].poll.return_value = True
        pipe_ends[0].recv.return_value = "READY"

        with patch.object(comm.mp, "Pipe", side_effect=[
            (pipe_ends[0], pipe_ends[1]),
            (pipe_ends[2], pipe_ends[3]),
            (pipe_ends[4], pipe_ends[5]),
        ]):
            with patch.object(comm.mp, "Process", return_value=process):
                with patch.object(comm.time, "sleep"):
                    connection.connect_serial("COM4")

        process.start.assert_called_once()
        self.assertTrue(connection.is_connected)
        for worker_endpoint in (pipe_ends[1], pipe_ends[3], pipe_ends[5]):
            worker_endpoint.close.assert_called_once()

    def test_startup_failure_reports_error_and_closes_all_pipe_ends(self):
        connection = comm.SerialConnection()
        pipe_ends = [Mock() for _ in range(6)]
        pipe_ends[0].poll.return_value = True
        pipe_ends[0].recv.return_value = "SERIAL_ERROR"
        pipe_ends[4].poll.return_value = True
        detail = "Could not open serial port COM4: Access denied"
        pipe_ends[4].recv.return_value = detail
        process = Mock()
        process.pid = 123
        process.is_alive.return_value = False

        with patch.object(comm.mp, "Pipe", side_effect=[
            (pipe_ends[0], pipe_ends[1]),
            (pipe_ends[2], pipe_ends[3]),
            (pipe_ends[4], pipe_ends[5]),
        ]):
            with patch.object(comm.mp, "Process", return_value=process):
                with self.assertRaisesRegex(comm.ConnectionError, detail):
                    connection.connect_serial("COM4")

        process.close.assert_called_once_with()
        for pipe in pipe_ends:
            pipe.close.assert_called_once_with()

    def test_disconnect_terminates_worker_that_does_not_exit(self):
        connection = comm.SerialConnection()
        connection.is_connected = True
        connection.proc = Mock()
        connection.proc.pid = 123
        connection.proc.is_alive.side_effect = [True, True, False, False]
        connection.proc_pipe_p = Mock()
        connection.ctrl_pipe_p = Mock()
        connection.ctrl_pipe_c = Mock()
        connection.data_pipe_p = Mock()
        connection.data_pipe_c = Mock()
        ctrl_pipe = connection.ctrl_pipe_p
        pipes = (
            connection.proc_pipe_p,
            connection.ctrl_pipe_p,
            connection.ctrl_pipe_c,
            connection.data_pipe_p,
            connection.data_pipe_c,
        )

        connection.disconnect_serial()

        ctrl_pipe.send.assert_called_once_with("DISCONNECT")
        connection.proc.terminate.assert_called_once_with()
        connection.proc.close.assert_called_once_with()
        for pipe in pipes:
            pipe.close.assert_called_once_with()
        self.assertFalse(connection.is_connected)

    def test_worker_exits_if_disconnect_is_consumed_by_experiment(self):
        ser = Mock()
        ser.is_open = True
        ser.readline.side_effect = [b"@ACK 0\n", b"@RCV 0\n"]
        experiment = Mock()
        experiment.run.return_value = "DISCONNECT"
        proc_pipe = Mock()
        proc_pipe.poll.side_effect = [True]
        proc_pipe.recv.return_value = experiment
        ctrl_pipe = Mock()
        ctrl_pipe.poll.return_value = False

        with patch.object(comm.serial, "Serial", return_value=ser):
            result = comm._serial_process(
                "COM4", proc_pipe, ctrl_pipe, Mock()
            )

        self.assertEqual(result, 0)
        self.assertEqual(
            [call.args[0] for call in proc_pipe.send.call_args_list],
            ["READY", "DISCONNECT"],
        )
        ser.close.assert_called_once_with()

    def test_experiment_marks_disconnect_consumed_during_data_read(self):
        experiment = Experiment.__new__(Experiment)
        experiment.serial = Mock()
        experiment.ctrl_pipe = Mock()
        experiment.ctrl_pipe.poll.return_value = True
        experiment.ctrl_pipe.recv.return_value = "DISCONNECT"
        experiment.current_command = "ER1 0"

        with patch.object(comm.time, "sleep"):
            self.assertFalse(experiment.serial_handler())

        experiment.serial.write.assert_called_once_with(b"a")
        experiment.serial.reset_input_buffer.assert_called_once_with()
        self.assertTrue(experiment.disconnect_requested)

    def test_closed_control_pipe_exits_worker_and_closes_serial_port(self):
        ser = Mock()
        ser.is_open = True
        ser.readline.side_effect = [b"@ACK 0\n", b"@RCV 0\n"]
        control_pipe = Mock()
        control_pipe.poll.side_effect = BrokenPipeError("pipe closed")

        with patch.object(comm.serial, "Serial", return_value=ser):
            with patch.object(comm.time, "sleep"):
                result = comm._serial_process(
                    "COM4", Mock(), control_pipe, Mock()
                )

        self.assertEqual(result, 0)
        ser.close.assert_called_once()

    def test_startup_write_timeout_is_reported_to_parent(self):
        ser = Mock()
        ser.is_open = True
        ser.write.side_effect = serial.SerialTimeoutException("write timed out")
        proc_pipe = Mock()
        data_pipe = Mock()

        with patch.object(comm.serial, "Serial", return_value=ser) as serial_factory:
            with patch.object(comm.time, "sleep"):
                comm._serial_process("COM4", proc_pipe, Mock(), data_pipe)

        serial_factory.assert_called_once_with("COM4", timeout=0.5, write_timeout=3)
        data_pipe.send.assert_called_once_with(
            "Serial startup failed on COM4: write timed out"
        )
        proc_pipe.send.assert_called_once_with("SERIAL_ERROR")
        ser.close.assert_called_once()

    def test_version_check_returns_error_when_command_cannot_be_sent(self):
        data_pipe = Mock()

        with patch.object(comm, "_write_command", return_value=False):
            status = comm.VersionCheck().run(Mock(), Mock(), data_pipe)

        self.assertEqual(status, "SERIAL_ERROR")
        data_pipe.send.assert_called_once_with(
            "No response to the DStat version command."
        )


class SerialPipeTimeoutTests(unittest.TestCase):
    def test_blocking_process_read_has_a_timeout(self):
        connection = comm.SerialConnection()
        connection.proc_pipe_p = Mock()
        connection.proc_pipe_p.poll.return_value = False

        with self.assertRaisesRegex(comm.ConnectionError, "Timed out"):
            connection.get_proc(block=True, timeout=0)

    def test_blocking_data_read_has_a_timeout(self):
        connection = comm.SerialConnection()
        connection.data_pipe_p = Mock()
        connection.data_pipe_p.poll.return_value = False

        with self.assertRaisesRegex(comm.ConnectionError, "Timed out"):
            connection.get_data(block=True, timeout=0)

    def test_dead_process_pipe_is_reported_as_connection_error(self):
        connection = comm.SerialConnection()
        connection.proc_pipe_p = Mock()
        connection.proc_pipe_p.poll.side_effect = BrokenPipeError("pipe ended")

        with self.assertRaisesRegex(comm.ConnectionError, "process pipe"):
            connection.get_proc()

    def test_dead_data_pipe_is_reported_as_connection_error(self):
        connection = comm.SerialConnection()
        connection.data_pipe_p = Mock()
        connection.data_pipe_p.poll.side_effect = BrokenPipeError("pipe ended")

        with self.assertRaisesRegex(comm.ConnectionError, "data pipe"):
            connection.flush_data()


if __name__ == "__main__":
    unittest.main()
