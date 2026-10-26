"""Serial communication module.

Uses multiprocessing (same as the original) for the serial subprocess so that
blocking serial reads never stall the Qt event loop.  A QObject wrapper
(`SerialConnection`) exposes Qt signals so the rest of the application can
react to connect/disconnect events and incoming data.
"""

import time
import struct
import multiprocessing as mp
import logging
import queue          # thread-safe queue used to forward data to Qt side
from collections import OrderedDict

import serial
from serial.tools import list_ports
from packaging.version import Version as parse_version

from PyQt6.QtCore import QObject, pyqtSignal

from ..errors import InputError, VarError
from . import state

logger = logging.getLogger(__name__)
dstat_logger = logging.getLogger("{}.DSTAT".format(__name__))
exp_logger = logging.getLogger("{}.Experiment".format(__name__))


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class AlreadyConnectedError(Exception):
    pass


class NotConnectedError(Exception):
    pass


class ConnectionError(Exception):
    pass


class TransmitError(Exception):
    pass


def _close_serial_port(ser, logger_instance):
    if ser is None:
        return
    try:
        if ser.is_open:
            ser.close()
    except serial.SerialException:
        logger_instance.exception("Failed to close the serial port cleanly.")


# ---------------------------------------------------------------------------
# Protocol tracing
# ---------------------------------------------------------------------------

# Kinds of entry shown in the GUI protocol terminal.
TRACE_TX = "tx"       # GUI -> DStat
TRACE_RX = "rx"       # DStat -> GUI
TRACE_INFO = "info"   # firmware commentary / progress notes
TRACE_WARN = "warn"   # unexpected reply that was retried
TRACE_ERROR = "error"  # command that could not be delivered

# Bare data-frame markers are streamed once per sample; tracing them would
# flood the terminal, so they are counted and summarised instead.
TRACE_DATA_MARKERS = ("B",)


class SerialTrace:
    """Serial port proxy that mirrors protocol traffic into a queue.

    Every complete line written to or read from the instrument becomes a
    ``(kind, text)`` tuple pushed onto *trace_queue*.  Binary sample payloads
    are not traced: the protocol terminal only shows the command/response
    conversation.

    The proxy is created inside the serial subprocess and never crosses a
    process boundary, so it can safely hold a reference to the real port.
    """

    def __init__(self, ser, trace_queue=None):
        object.__setattr__(self, "_ser", ser)
        object.__setattr__(self, "_queue", trace_queue)
        object.__setattr__(self, "_data_frames", 0)

    # -- trace plumbing -------------------------------------------------
    def note(self, kind: str, text: str):
        """Queue a non-I/O protocol note (used by the command helpers)."""
        queue_obj = self._queue
        if queue_obj is None:
            return
        try:
            queue_obj.put_nowait((kind, text))
        except (queue.Full, ValueError, OSError):
            pass

    def _emit(self, kind: str, text: str):
        text = text.rstrip("\r\n")
        if not text:
            return
        if kind == TRACE_RX and text.strip() in TRACE_DATA_MARKERS:
            frames = self._data_frames + 1
            object.__setattr__(self, "_data_frames", frames)
            if frames % 200 == 0:
                self.note(TRACE_INFO, "Ã¢â‚¬Â¦ {} data frames received".format(frames))
            return
        if kind == TRACE_RX and text.lstrip().startswith("#"):
            kind = TRACE_INFO
        self.note(kind, text)

    # -- serial API -----------------------------------------------------
    def write(self, data):
        if isinstance(data, (bytes, bytearray)):
            text = bytes(data).decode("utf-8", "replace")
        else:
            text = str(data)
        for line in text.splitlines():
            self._emit(TRACE_TX, line)
        return self._ser.write(data)

    def readline(self, *args, **kwargs):
        line = self._ser.readline(*args, **kwargs)
        if line:
            self._emit(TRACE_RX, bytes(line).decode("utf-8", "replace"))
        return line

    def read(self, *args, **kwargs):
        # Binary sample payloads are not part of the text protocol.
        return self._ser.read(*args, **kwargs)

    def __iter__(self):
        return iter(self.readline, b"")

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_ser"), name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            setattr(object.__getattribute__(self, "_ser"), name, value)


def _trace_note(ser, kind: str, text: str):
    """Send a note through *ser* when it is a SerialTrace, otherwise ignore."""
    note = getattr(ser, "note", None)
    if callable(note):
        note(kind, text)


# ---------------------------------------------------------------------------
# Serial subprocess
# ---------------------------------------------------------------------------

def _serial_process(ser_port, proc_pipe, ctrl_pipe, data_pipe, trace_queue=None):
    """Runs in a separate Process.  Manages the physical serial port and
    dispatches experiment objects received on *proc_pipe*.
    """
    ser_logger = logging.getLogger("{}._serial_process".format(__name__))
    ser = None
    last_error = None

    for attempt in range(5):
        try:
            ser = serial.Serial(ser_port, timeout=0.5, write_timeout=3)
            break
        except serial.SerialException as exc:
            last_error = exc
            if attempt < 4:
                time.sleep(0.25)

    try:
        if ser is None or not ser.is_open:
            raise ConnectionError(
                f"Could not open serial port {ser_port}: "
                f"{last_error or 'port is closed'}"
            )

        # Every read/write from this point on is mirrored to the protocol
        # terminal in the GUI.
        trace = SerialTrace(ser, trace_queue)

        # Original startup handshake (unchanged from baseline).
        trace.write(b'!0 ')

        for _ in range(12):
            line = trace.readline().rstrip().decode(errors="replace")
            if line == "@ACK 0":
                reply = trace.readline().rstrip().decode(errors="replace")
                if reply == "@RCV 0":
                    break
        else:
            raise serial.SerialException(
                f"No valid startup handshake received from {ser_port}."
            )

        # Let the device settle before accepting further commands.
        time.sleep(0.5)
        try:
            for _ in range(5):
                n = getattr(ser, "in_waiting", 0)
                if n:
                    ser.read(n)
                time.sleep(0.1)
        except Exception:
            pass

        trace.note(TRACE_INFO, "handshake complete on {}".format(ser_port))
        proc_pipe.send("READY")
    except (serial.SerialException, ConnectionError, OSError) as exc:
        ser_logger.error("Serial startup failed on %s: %s", ser_port, exc)
        for pipe, message in (
            (data_pipe, f"Serial startup failed on {ser_port}: {exc}"),
            (proc_pipe, "SERIAL_ERROR"),
        ):
            try:
                pipe.send(message)
            except (BrokenPipeError, EOFError, OSError):
                pass
        _close_serial_port(ser, ser_logger)
        return 1

    try:
        while True:
            try:
                if ctrl_pipe.poll():
                    ctrl_buffer = ctrl_pipe.recv()
                    if ctrl_buffer in ("a", "DISCONNECT"):
                        proc_pipe.send("ABORT")
                        trace.write(b'a')
                        if ctrl_buffer == "DISCONNECT":
                            ser.rts = False
                            try:
                                ser._update_dtr_state()
                            except AttributeError:
                                pass
                            proc_pipe.send("DISCONNECT")
                            return 0
                    else:
                        trace.write(
                            ctrl_buffer.encode()
                            if isinstance(ctrl_buffer, str)
                            else ctrl_buffer
                        )

                elif proc_pipe.poll():
                    while ctrl_pipe.poll():
                        ctrl_pipe.recv()
                    try:
                        return_code = proc_pipe.recv().run(trace, ctrl_pipe, data_pipe)
                    except serial.SerialException as exc:
                        ser_logger.error("Serial communication failed: %s", exc)
                        try:
                            proc_pipe.send("DISCONNECT")
                        except (BrokenPipeError, EOFError, OSError):
                            pass
                        return 0
                    if return_code == "DISCONNECT":
                        try:
                            proc_pipe.send("DISCONNECT")
                        except (BrokenPipeError, EOFError, OSError):
                            pass
                        return 0
                    proc_pipe.send(return_code)

                else:
                    time.sleep(0.1)
            except (BrokenPipeError, EOFError, OSError):
                # The GUI owns the other ends; closing it is a normal shutdown.
                return 0
            except serial.SerialException as exc:
                ser_logger.error("Serial communication failed: %s", exc)
                return 0
    finally:
        _close_serial_port(ser, ser_logger)


# ---------------------------------------------------------------------------
# SerialDevices helper
# ---------------------------------------------------------------------------

class SerialDevices:
    """Enumerate available serial ports."""

    def __init__(self):
        self.refresh()

    def refresh(self):
        self.ports = [p.device for p in list_ports.comports()]
        self.ports.sort()


# ---------------------------------------------------------------------------
# Qt-aware serial connection wrapper
# ---------------------------------------------------------------------------

class SerialConnection(QObject):
    """Manages the serial subprocess and exposes Qt signals."""

    connected = pyqtSignal()
    disconnected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_connected = False
        self.last_error = None
        self.proc = None
        self.trace_queue = None
        self._trace_backlog = []

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect_serial(self, ser_port: str):
        if self.is_connected:
            raise AlreadyConnectedError("Already connected.")

        self.proc_pipe_p, self.proc_pipe_c = mp.Pipe(duplex=True)
        self.ctrl_pipe_p, self.ctrl_pipe_c = mp.Pipe(duplex=True)
        self.data_pipe_p, self.data_pipe_c = mp.Pipe(duplex=True)
        # Bounded so a stalled GUI can never grow the subprocess memory.
        self.trace_queue = mp.Queue(maxsize=20000)
        self._trace_backlog = []

        try:
            self.proc = mp.Process(
                target=_serial_process,
                args=(
                    ser_port,
                    self.proc_pipe_c,
                    self.ctrl_pipe_c,
                    self.data_pipe_c,
                    self.trace_queue,
                ),
                daemon=True,
            )
            self.proc.start()
        except Exception:
            for name in ("proc_pipe_c", "ctrl_pipe_c", "data_pipe_c"):
                pipe = getattr(self, name, None)
                if pipe is not None:
                    pipe.close()
                    setattr(self, name, None)
            self._cleanup_process()
            raise

        # The child has duplicated these endpoints; keep only the parent ends here.
        for name in ("proc_pipe_c", "ctrl_pipe_c", "data_pipe_c"):
            pipe = getattr(self, name, None)
            if pipe is not None:
                pipe.close()
                setattr(self, name, None)

        deadline = time.monotonic() + 20
        try:
            while time.monotonic() < deadline:
                if self.proc_pipe_p.poll(0.05):
                    status = self.proc_pipe_p.recv()
                    if status == "READY":
                        self.is_connected = True
                        self.connected.emit()
                        return
                    if status == "SERIAL_ERROR":
                        detail = (
                            self.data_pipe_p.recv()
                            if self.data_pipe_p.poll()
                            else None
                        )
                        raise ConnectionError(
                            detail or "Serial process failed to start."
                        )
                    logger.warning("Unexpected serial startup status: %s", status)

                if not self.proc.is_alive():
                    detail = (
                        self.data_pipe_p.recv()
                        if self.data_pipe_p.poll()
                        else None
                    )
                    raise ConnectionError(
                        detail or "Serial process failed to start."
                    )

            raise ConnectionError(
                f"Timed out waiting for the serial process to initialize on {ser_port}."
            )
        except Exception:
            self._cleanup_process()
            raise

    def disconnect_serial(self):
        if not self.is_connected:
            if self.proc is not None:
                self._cleanup_process()
            return
        self.is_connected = False
        self._cleanup_process(request_disconnect=True)
        self.disconnected.emit()

    def _cleanup_process(self, request_disconnect: bool = False):
        """Stop the serial worker and close all process and pipe handles."""
        self._drain_trace_queue()
        proc = self.proc
        if proc is not None:
            try:
                started = proc.pid is not None
                if started and proc.is_alive():
                    if request_disconnect and self.ctrl_pipe_p is not None:
                        try:
                            self.ctrl_pipe_p.send("DISCONNECT")
                        except (BrokenPipeError, EOFError, OSError) as exc:
                            logger.warning(
                                "Could not signal serial process to disconnect: %s",
                                exc,
                            )
                    proc.join(timeout=2 if request_disconnect else 1)
                    if proc.is_alive():
                        logger.warning(
                            "Serial worker did not stop gracefully; terminating it."
                        )
                        proc.terminate()
                        proc.join(timeout=2)
                    if proc.is_alive():
                        logger.error("Serial worker survived termination; killing it.")
                        proc.kill()
                        proc.join(timeout=2)
            finally:
                if proc.pid is None or not proc.is_alive():
                    proc.close()

        for name in (
            "proc_pipe_p", "proc_pipe_c",
            "ctrl_pipe_p", "ctrl_pipe_c",
            "data_pipe_p", "data_pipe_c",
        ):
            pipe = getattr(self, name, None)
            if pipe is not None:
                try:
                    pipe.close()
                except (OSError, ValueError):
                    logger.debug("Serial pipe %s was already closed.", name)
                setattr(self, name, None)

        # Queued trace entries were already moved into the backlog, so the
        # queue itself can be released here.
        trace_queue = self.trace_queue
        if trace_queue is not None:
            self._drain_trace_queue()
            try:
                trace_queue.close()
            except (OSError, ValueError):
                logger.debug("Serial trace queue was already closed.")
            self.trace_queue = None

    def assert_connected(self):
        if not self.is_connected:
            raise NotConnectedError("Not connected.")

    # ------------------------------------------------------------------
    # Experiment control
    # ------------------------------------------------------------------

    def start_exp(self, exp):
        self.assert_connected()
        try:
            self.proc_pipe_p.send(exp)
        except (BrokenPipeError, EOFError, OSError, ValueError) as exc:
            raise ConnectionError("Serial process pipe is no longer available.") from exc

    def stop_exp(self):
        self.send_ctrl("a")

    def send_ctrl(self, cmd: str):
        self.assert_connected()
        try:
            self.ctrl_pipe_p.send(cmd)
        except (BrokenPipeError, EOFError, OSError, ValueError) as exc:
            raise ConnectionError("Serial control pipe is no longer available.") from exc

    # ------------------------------------------------------------------
    # Polling helpers (called from Qt timers)
    # ------------------------------------------------------------------

    def get_data(self, block: bool = False, timeout: float | None = None):
        """Return next data tuple from the data pipe, or None."""
        try:
            if block:
                if not self.data_pipe_p.poll(timeout):
                    raise ConnectionError("Timed out waiting for serial data.")
                return self.data_pipe_p.recv()
            if self.data_pipe_p.poll():
                return self.data_pipe_p.recv()
            return None
        except (BrokenPipeError, EOFError, OSError, ValueError) as exc:
            raise ConnectionError("Serial data pipe is no longer available.") from exc

    def get_proc(self, block: bool = False, timeout: float | None = None):
        """Return next proc message, or None."""
        try:
            if block:
                if not self.proc_pipe_p.poll(timeout):
                    raise ConnectionError("Timed out waiting for the serial process.")
                return self.proc_pipe_p.recv()
            if self.proc_pipe_p.poll():
                return self.proc_pipe_p.recv()
            return None
        except (BrokenPipeError, EOFError, OSError, ValueError) as exc:
            raise ConnectionError("Serial process pipe is no longer available.") from exc

    def get_ctrl(self, block: bool = False):
        """Return next ctrl message, or None."""
        try:
            if block or self.ctrl_pipe_p.poll():
                return self.ctrl_pipe_p.recv()
            return None
        except (BrokenPipeError, EOFError, OSError, ValueError) as exc:
            raise ConnectionError("Serial control pipe is no longer available.") from exc

    def flush_data(self):
        """Discard any unread data left over from a previous experiment."""
        try:
            while self.data_pipe_p.poll():
                self.data_pipe_p.recv()
        except (BrokenPipeError, EOFError, OSError, ValueError) as exc:
            raise ConnectionError("Serial data pipe is no longer available.") from exc

    # ------------------------------------------------------------------
    # Protocol trace
    # ------------------------------------------------------------------

    def get_trace(self, limit: int = 500):
        """Return pending ``(kind, text)`` protocol entries.

        Entries are drained in batches so a stalled event loop cannot spend an
        unbounded amount of time in a single call.
        """
        if not self._trace_backlog and self.trace_queue is None:
            return []

        self._drain_trace_queue(limit=limit)
        entries = self._trace_backlog[:limit]
        del self._trace_backlog[:len(entries)]
        return entries

    def _drain_trace_queue(self, limit: int = 2000):
        """Move whatever the serial subprocess produced into the backlog."""
        if self.trace_queue is None:
            return
        while len(self._trace_backlog) < limit:
            try:
                self._trace_backlog.append(self.trace_queue.get_nowait())
            except queue.Empty:
                break
            except (EOFError, OSError, ValueError):
                break


    def flush_proc(self):
        """Discard any unread return codes left over from a previous run."""
        try:
            while self.proc_pipe_p.poll():
                self.proc_pipe_p.recv()
        except (BrokenPipeError, EOFError, OSError, ValueError) as exc:
            raise ConnectionError("Serial process pipe is no longer available.") from exc


# ---------------------------------------------------------------------------
# Low level protocol helpers (run inside the serial subprocess)
# ---------------------------------------------------------------------------

def _read_reply(ser, retries: int = 3) -> str:
    """Read one reply line, transparently consuming human-readable '#' info.

    Raises TransmitError when *retries* consecutive reads come back empty.
    """
    while True:
        reply = ser.readline().rstrip().decode(errors="replace")
        if reply.startswith("#"):
            dstat_logger.info(reply)
        elif reply == "":
            retries -= 1
            if retries <= 0:
                raise TransmitError()
        else:
            return reply


def _write_command(ser, cmd: str, retries: int = 5) -> bool:
    """Send '!n\\n<cmd>\\n' and verify the @ACK / @RCV handshake.

    The firmware uses *n* only as a size hint; it then reads the command with
    fgets() up to the newline, so a trailing space inside *cmd* is preserved
    and counted by strlen().
    """
    n = len(cmd)

    for _ in range(retries):
        ser.reset_input_buffer()
        ser.write("!{}\n".format(n).encode())
        time.sleep(0.1)

        try:
            reply = _read_reply(ser)
        except TransmitError:
            continue

        if reply != "@ACK {}".format(n):
            logger.warning("Expected ACK %s got: %s", n, reply)
            _trace_note(ser, TRACE_WARN, "expected @ACK {}, got {!r}".format(n, reply))
            continue

        ser.write("{}\n".format(cmd).encode())

        try:
            reply = _read_reply(ser)
        except TransmitError:
            continue

        if reply != "@RCV {}".format(n):
            logger.warning("Expected RCV %s got: %s", n, reply)
            _trace_note(ser, TRACE_WARN, "expected @RCV {}, got {!r}".format(n, reply))
            continue

        return True

    logger.error("Could not write command: %s", cmd)
    _trace_note(ser, TRACE_ERROR, "command not delivered: {!r}".format(cmd))
    return False


def _iter_until_done(ser, timeout: float = 10.0):
    """Yield decoded status lines until '@DONE' or *timeout* seconds elapse.

    Human-readable '#' lines are logged and skipped so that callers only see
    real status/result lines.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        raw = ser.readline()
        if not raw:
            continue
        line = raw.rstrip().decode(errors="replace")
        if line.startswith("#"):
            dstat_logger.info(line)
            continue
        if line.startswith("@DONE"):
            return
        yield line


# ---------------------------------------------------------------------------
# Version check
# ---------------------------------------------------------------------------

class VersionCheck:
    """Ask the DStat for its PCB / firmware version ('V')."""

    def __init__(self):
        pass

    def run(self, ser, ctrl_pipe, data_pipe):
        """Send 'V' and return '(pcb_version, firmware_version)'."""
        version_string = None

        try:
            if _write_command(ser, "V"):
                for line in _iter_until_done(ser):
                    if line.startswith("V"):
                        version_string = line.lstrip("V").strip()
                    else:
                        dstat_logger.debug(line)
                ser.reset_input_buffer()
            else:
                data_pipe.send("No response to the DStat version command.")
                return "SERIAL_ERROR"
        except serial.SerialException:
            data_pipe.send("Serial error while requesting the DStat version.")
            return "SERIAL_ERROR"

        if not version_string:
            logger.warning("No version string received; assuming old firmware.")
            data_pipe.send((None, None))
            return "DONE"

        # Format is "<major>.<minor>.<micro>-<git_commit_decimal>"
        pcb, _, firmware = version_string.rpartition("-")
        if pcb == "":
            # Firmware too old to report a git revision.
            pcb = version_string
            firmware = None

        logger.info("PCB version: %s", pcb)
        logger.info("Firmware version: %s", firmware)

        data_pipe.send((pcb, firmware))
        return "DONE"


def version_check() -> bool:
    """Read the version from the already-connected DStat into `state`."""
    state.ser.flush_data()
    state.ser.flush_proc()
    state.ser.start_exp(VersionCheck())

    status = state.ser.get_proc(block=True, timeout=40)
    if status != "DONE":
        logger.error("Version check failed with serial process status: %s", status)
        if status == "SERIAL_ERROR":
            try:
                state.ser.last_error = state.ser.get_data(block=True, timeout=2)
            except ConnectionError:
                logger.debug("Serial process did not provide diagnostic details.")
        state.dstat_version = None
        state.firmware_version = None
        return False

    pcb, state.firmware_version = state.ser.get_data(block=True, timeout=5)

    if pcb is None:
        state.dstat_version = None
    else:
        try:
            state.dstat_version = parse_version(pcb)
        except Exception:
            logger.warning("Could not parse version string %s", pcb)
            state.dstat_version = None

    logger.debug("version_check done")
    return True


def supports_ocp() -> bool:
    """OCP / potentiometry ('P') requires firmware v1.2 or newer."""
    if state.board_instance is None:
        return False
    return bool(getattr(state.board_instance, "ocp_supported", False))


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

# Order is significant: the firmware's sscanf() for 'SW' expects exactly
# these fields, in this order, space separated.
SETTINGS_ORDER = [
    "max5443_offset",
    "tcs_enabled",
    "tcs_clear_threshold",
    "r100_trim",
    "r3k_trim",
    "r30k_trim",
    "r300k_trim",
    "r3M_trim",
    "r30M_trim",
    "r100M_trim",
    "eis_cal1",
    "eis_cal2",
    "dac_units_true",
]


class Settings:
    """Read ('r') and/or write ('w') the DStat EEPROM settings.

    Reads return an OrderedDict mapping name -> [index, value] so that the
    write path can rebuild the value list in the original order.
    """

    def __init__(self, task: str, settings=None):
        self.task = task
        self.settings = settings or OrderedDict()

    def run(self, ser, ctrl_pipe, data_pipe):
        self.ser = ser

        if "w" in self.task:
            self._write()

        if "r" in self.task:
            data_pipe.send(self._read())

        return "DONE"

    def _read(self) -> OrderedDict:
        settings = OrderedDict()

        if not _write_command(self.ser, "SR"):
            return settings

        payload = None
        for line in _iter_until_done(self.ser):
            if line.startswith("S"):
                payload = line.lstrip("S").strip()
        self.ser.reset_input_buffer()

        if not payload:
            logger.warning("No settings string received.")
            return settings

        for i, pair in enumerate(payload.split(":")):
            name, _, value = pair.partition(".")
            if not name:
                continue
            try:
                parsed = int(value)
            except ValueError:
                parsed = value
            settings[name] = [i, parsed]

        return settings

    def _write(self) -> bool:
        values = []
        for name in SETTINGS_ORDER:
            entry = self.settings.get(name)
            if entry is None:
                logger.error("Missing setting %s; refusing to write.", name)
                return False
            values.append(str(entry[1]))

        cmd = "SW" + " ".join(values) + " "
        return _write_command(self.ser, cmd)


def read_settings(retries: int = 2):
    """Populate `state.settings` from the connected DStat."""
    last_exc = None
    for attempt in range(retries + 1):
        try:
            state.ser.flush_data()
            state.ser.flush_proc()
            state.ser.start_exp(Settings(task="r"))

            data = state.ser.get_data(block=True, timeout=20)
            state.settings = data or OrderedDict()
            proc = state.ser.get_proc(block=True, timeout=20)
            logger.info("Read settings from DStat (attempt %d)", attempt + 1)
            logger.debug("read_settings proc: %s", proc)
            return state.settings
        except Exception as exc:
            last_exc = exc
            logger.warning("read_settings attempt %d failed: %s", attempt + 1, exc)
            time.sleep(0.5)
    logger.error("read_settings failed after %d attempts: %s", retries + 1, last_exc)
    state.settings = OrderedDict()
    return state.settings


def write_settings():
    """Write `state.settings` back to the DStat EEPROM."""
    logger.debug("Settings to write: %s", state.settings)

    state.ser.flush_data()
    state.ser.flush_proc()
    state.ser.start_exp(Settings(task="w", settings=state.settings))

    status = state.ser.get_proc(block=True, timeout=15)
    logger.info("Wrote settings to DStat (status: %s)", status)
    return status


# ---------------------------------------------------------------------------
# Light sensor (TCS)
# ---------------------------------------------------------------------------

class LightSensor:
    """Read the TCS light sensor ('T').

    The firmware answers with 'T<clear>.<red>.<green>.<blue>' where every
    channel is '-1' when the sensor is disabled in the settings.
    """

    def __init__(self):
        pass

    def run(self, ser, ctrl_pipe, data_pipe):
        clear = None

        try:
            if _write_command(ser, "T"):
                for line in _iter_until_done(ser):
                    if line.startswith("T"):
                        parts = line.lstrip("T").strip().split(".")
                        try:
                            clear = int(parts[0])
                        except (ValueError, IndexError):
                            clear = None
                ser.reset_input_buffer()
            else:
                return "DONE"
        except serial.SerialException:
            return "SERIAL_ERROR"

        data_pipe.send(clear)
        return "DONE"


def read_light_sensor():
    """Return the TCS clear-channel reading, or None when unavailable."""
    state.ser.flush_data()
    state.ser.flush_proc()
    state.ser.start_exp(LightSensor())

    logger.debug("read_light_sensor proc: %s", state.ser.get_proc(block=True))
    return state.ser.get_data(block=True)
