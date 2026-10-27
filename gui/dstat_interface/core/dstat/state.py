"""Global application state shared across modules."""
from collections import OrderedDict

# Serial connection instance (SerialConnection)
ser = None

# DStat hardware version string
dstat_version = None

# Firmware version string
firmware_version = None

# Active board instance (BaseBoard subclass)
board_instance = None

# ADC / potentiostat settings dict
settings = OrderedDict()


def reset():
    """Reset all state to defaults."""
    global ser, dstat_version, firmware_version, board_instance, settings
    ser = None
    dstat_version = None
    firmware_version = None
    board_instance = None
    settings = OrderedDict()
