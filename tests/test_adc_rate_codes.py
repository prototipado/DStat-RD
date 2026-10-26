import unittest
from unittest.mock import Mock

from dstat_interface.core.interface.main_window import ADC_RATES
from dstat_interface.core.params import _set_params


class AdcRateCodeTests(unittest.TestCase):
    def test_rate_codes_match_firmware_hex_values(self):
        self.assertEqual(
            [int(code, 16) for _, code in ADC_RATES],
            [0x03, 0x13, 0x23, 0x33, 0x43, 0x53, 0x63, 0x72,
             0x82, 0x92, 0xA1, 0xB0, 0xC0, 0xD0, 0xE0, 0xF0],
        )
        self.assertEqual(ADC_RATES[6], ("50 Hz", "63"))

    def test_loads_legacy_decimal_adc_rate(self):
        window = Mock()

        _set_params(window, {"adc_rate": "99"})

        window.adc_rate_combo.setCurrentIndex.assert_called_once_with(6)

    def test_loads_hex_adc_rate(self):
        window = Mock()

        _set_params(window, {"adc_rate": "63"})

        window.adc_rate_combo.setCurrentIndex.assert_called_once_with(6)


if __name__ == "__main__":
    unittest.main()
