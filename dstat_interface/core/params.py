"""Parameter serialisation helpers."""

import logging

import yaml

from .errors import InputError

logger = logging.getLogger(__name__)


def save_params(window, path: str):
    """Collect current UI parameters and save to *path* as YAML."""
    params = _get_params(window)
    with open(path, "w") as f:
        yaml.dump(params, f)
    logger.info("Parameters saved to %s", path)


def load_params(window, path: str):
    """Load parameters from YAML *path* and apply to the UI."""
    with open(path, "r") as f:
        params = yaml.safe_load(f)
    _set_params(window, params)


def _get_params(window) -> dict:
    params: dict = {}

    exp_id = window.exp_panel.current_id
    params["experiment_index"] = exp_id
    params.update(window.exp_panel.get_params())

    # ADC / gain
    from .interface.main_window import ADC_PGA, ADC_RATES
    params["adc_pga"]    = ADC_PGA[window.adc_pga_combo.currentIndex()][1]
    params["adc_rate"]   = ADC_RATES[window.adc_rate_combo.currentIndex()][1]
    params["buffer_true"] = window.buffer_check.isChecked()
    params["short_true"]  = window.short_check.isChecked()
    params["gain"]       = window.gain_combo.currentData() or 2

    return params


def _set_params(window, params: dict):
    from .interface.main_window import ADC_PGA, ADC_RATES

    if "experiment_index" in params:
        window.exp_panel.set_params(params["experiment_index"], params)

    if "adc_pga" in params:
        for i, (_, val) in enumerate(ADC_PGA):
            if val == str(params["adc_pga"]):
                window.adc_pga_combo.setCurrentIndex(i)
                break

    if "adc_rate" in params:
        rate_index_by_code = {
            val: i for i, (_, val) in enumerate(ADC_RATES)
        }
        rate_code = str(params["adc_rate"])
        rate_index = rate_index_by_code.get(rate_code)
        if rate_index is None:
            legacy_codes = {
                str(int(val, 16)): val for _, val in ADC_RATES
            }
            legacy_code = legacy_codes.get(rate_code)
            if legacy_code is not None:
                rate_index = rate_index_by_code[legacy_code]
        if rate_index is not None:
            window.adc_rate_combo.setCurrentIndex(rate_index)

    if "buffer_true" in params:
        window.buffer_check.setChecked(bool(params["buffer_true"]))

    if "short_true" in params:
        window.short_check.setChecked(bool(params["short_true"]))
