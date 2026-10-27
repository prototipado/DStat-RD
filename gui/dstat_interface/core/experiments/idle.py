import struct
import time

from ..dstat import state


class OCPExp:
    """Open circuit potential measurement (displayed in status bar)."""

    id = "ocp"

    def __init__(self):
        self.re_voltage_scale = state.board_instance.re_voltage_scale
        self.databytes = 8
        self.commands = [
            "EA2 3 1 ",   # buffer on, 2.5 Hz, 2x PGA
            "EP0 0 ",
        ]

    def data_handler(self, data_input):
        scan, data = data_input
        seconds, milliseconds, voltage = struct.unpack("<HHl", data)
        return voltage / 5.592405e6 * self.re_voltage_scale

    def run(self, ser, ctrl_pipe, data_pipe):
        import serial as _serial
        self.serial = ser
        self.ctrl_pipe = ctrl_pipe
        self.data_pipe = data_pipe

        try:
            for cmd in self.commands:
                self.serial.write("!{}\n".format(len(cmd)).encode())
                time.sleep(0.1)
                self.serial.readline()  # ACK
                self.serial.write("{}\n".format(cmd).encode())
                self.serial.readline()  # RCV
        except _serial.SerialException:
            return "SERIAL_ERROR"

        try:
            while True:
                if self.ctrl_pipe.poll():
                    inp = self.ctrl_pipe.recv()
                    if inp in ("a", "DISCONNECT"):
                        self.serial.write(b"a")
                        return "DISCONNECT" if inp == "DISCONNECT" else "DONE"
                for line in self.serial:
                    line = line.rstrip().decode(errors="replace")
                    if line.startswith("B"):
                        raw = self.serial.read(size=self.databytes)
                        value = self.data_handler((0, raw))
                        self.data_pipe.send(value)
                    elif line.lstrip().startswith("@DONE"):
                        return "DONE"
        except _serial.SerialException:
            return "SERIAL_ERROR"

        return "DONE"
