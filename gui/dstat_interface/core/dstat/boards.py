"""DStat board definitions.

Each class represents a hardware revision of the DStat potentiostat and stores
gain resistor values, labels and voltage-scale factors.
"""
import logging
from packaging.version import Version as parse_version

logger = logging.getLogger(__name__)


class BaseBoard:
    pcb_version = "x.x.x"
    booster = False
    # Firmware only implements potentiometry ('P') / OCP from v1.2 onwards.
    ocp_supported = False

    def __init__(self):
        self.max_freq = 5000
        self.max_scans = 255
        self.max_time = 65535
        self.setup()
        assert len(self.gain) == self.gain_settings
        assert len(self.gain_labels) == self.gain_settings
        if self.gain_trim is not None:
            assert len(self.gain_trim) == self.gain_settings

    def setup(self):
        """Override in subclasses to provide correct numbers."""
        self.gain = [1, 1e2, 3e3, 3e4, 3e5, 3e6, 3e7, 1e8]
        self.gain_labels = [
            "Bypass",
            "100 Ω (15 mA FS)",
            "3 kΩ (500 µA FS)",
            "30 kΩ (50 µA FS)",
            "300 kΩ (5 µA FS)",
            "3 MΩ (500 nA FS)",
            "30 MΩ (50 nA FS)",
            "100 MΩ (15 nA FS)",
        ]
        self.gain_trim = [
            None, "r100_trim", "r3k_trim", "r30k_trim",
            "r300k_trim", "r3M_trim", "r30M_trim", "r100M_trim",
        ]
        self.gain_settings = len(self.gain)
        self.gain_default_index = 2
        self.re_voltage_scale = 1

    def test_mv(self, mv):
        """Return True if voltage in mV is within the DAC range."""
        dac = float(mv) * self.re_voltage_scale / (3000.0 / 65536) + 32768
        return 0 <= dac <= 65535

    def test_freq(self, hz):
        return 0 < float(hz) < self.max_freq

    def test_scans(self, n):
        return 0 < int(n) < self.max_scans

    def test_s(self, s):
        return 0 < int(s) < self.max_time


class V1_1Board(BaseBoard):
    pcb_version = "1.1"

    def setup(self):
        self.gain = [1e2, 3e2, 3e3, 3e4, 3e5, 3e6, 3e7, 5e8]
        self.gain_labels = [
            None,
            "300 Ω (5 mA FS)",
            "3 kΩ (500 µA FS)",
            "30 kΩ (50 µA FS)",
            "300 kΩ (5 µA FS)",
            "3 MΩ (500 nA FS)",
            "30 MΩ (50 nA FS)",
            "500 MΩ (3 nA FS)",
        ]
        self.gain_trim = None
        self.gain_settings = len(self.gain)
        self.gain_default_index = 2
        self.re_voltage_scale = 1


class V1_2Board(BaseBoard):
    pcb_version = "1.2"
    ocp_supported = True

    def setup(self):
        self.gain = [1, 1e2, 3e3, 3e4, 3e5, 3e6, 3e7, 1e8]
        self.gain_labels = [
            "Bypass",
            "100 Ω (15 mA FS)",
            "3 kΩ (500 µA FS)",
            "30 kΩ (50 µA FS)",
            "300 kΩ (5 µA FS)",
            "3 MΩ (500 nA FS)",
            "30 MΩ (50 nA FS)",
            "100 MΩ (15 nA FS)",
        ]
        self.gain_trim = [
            None, "r100_trim", "r3k_trim", "r30k_trim",
            "r300k_trim", "r3M_trim", "r30M_trim", "r100M_trim",
        ]
        self.gain_settings = len(self.gain)
        self.gain_default_index = 2
        self.re_voltage_scale = 1


# Map from firmware version string to board class
BOARD_MAP = {
    "1.1": V1_1Board,
    "1.2": V1_2Board,
}


def get_board(version_string: str) -> BaseBoard:
    """Return the appropriate board instance for a firmware version string."""
    try:
        ver = parse_version(version_string)
        for key in sorted(BOARD_MAP.keys(), key=parse_version, reverse=True):
            if ver >= parse_version(key):
                return BOARD_MAP[key]()
    except Exception:
        logger.warning("Could not determine board for version %s, using BaseBoard", version_string)
    return BaseBoard()
