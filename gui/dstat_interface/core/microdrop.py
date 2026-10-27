"""µDrop (microdrop) connection over ZMQ.

Python 3 / pyzmq port of the original `dstat_interface/microdrop.py`.

The DStat interface binds a ZMQ REP socket; an external µDrop controller
connects and drives the experiment remotely:

    controller                     DStat interface
    ---------                      --------------
    "start"        -------------->  STARTEXP
                   <-------------  START_REP  ("started")
    experiment runs
    "notify_completion" -----------> EXP_FINISH_REQ
                   <-------------  EXPFINISHED ("completed")
"""

try:
    import zmq
except ImportError:  # pragma: no cover - exercised only without pyzmq
    zmq = None

import logging

logger = logging.getLogger(__name__)

# Signals
CONREQ = "0"
CONREP = "1"
STARTEXP = "start"
START_REP = "started"
EXP_FINISH_REQ = "notify_completion"
EXPFINISHED = "completed"
INVAL_CMD = "99"

# States
RECV = 0
SEND = 1


class MicrodropUnavailableError(ImportError):
    """Raised when pyzmq is not installed."""


class microdropConnection:
    """Manages the microdrop connection over TCP with zmq."""

    def __init__(self, port=6789):
        """Create the zmq context and bind the REP socket to *port*.

        Must be called manually to re-initialise after :meth:`reset`.
        """
        if zmq is None:
            raise MicrodropUnavailableError(
                "The 'pyzmq' package is required for µDrop support.\n"
                "Install it with:  pip install pyzmq"
            )

        self.port = port
        self.connected = False
        self.state = RECV

        self.ctx = zmq.Context()
        self.soc = zmq.Socket(self.ctx, zmq.REP)
        self.soc.bind("tcp://*:{}".format(self.port))

        logger.info("microdrop listening on port %s", self.port)

    def listen(self):
        """Non-blocking receive on the zmq socket.

        `self.state` must be RECV.

        Returns:
            tuple -- ``(True, message)`` when a message arrived, otherwise
            ``(False, "")``.
        """
        if self.state == SEND:
            logger.warning("microdrop-listen: connection state invalid, resetting.")
            self.reset()
            self.__init__(self.port)
            return (False, "")

        try:
            message = self.soc.recv(flags=zmq.NOBLOCK, copy=True)
            self.state = SEND
            self.connected = True
            return (True, message)
        except zmq.Again:
            return (False, "")

    def reply(self, data):
        """Send a reply on the zmq socket. `self.state` must be SEND."""
        if self.state == RECV:
            logger.warning("microdrop-reply: connection state invalid, resetting.")
            self.reset()
            self.__init__(self.port)
            return False

        self.state = RECV
        if isinstance(data, str):
            data = data.encode()
        self.soc.send(data)
        return True

    def reset(self):
        """Tear down the zmq socket and context.

        Call ``__init__`` again afterwards to re-bind the port.
        """
        try:
            if getattr(self, "soc", None) is not None:
                self.soc.close(linger=0)
        except Exception as e:
            logger.warning("Error closing microdrop socket: %s", e)
        try:
            if getattr(self, "ctx", None) is not None:
                self.ctx.term()
        except Exception as e:
            logger.warning("Error terminating microdrop context: %s", e)

        self.soc = None
        self.ctx = None
        self.connected = False
        self.state = RECV