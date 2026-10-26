"""Parameter validation against DStat hardware limits.

The original GTK interface performed these checks inline in
`on_pot_start_clicked`.  Here they are expressed as a declarative table so the
same rules are reused by every front-end and are testable in isolation.
"""

from .errors import InputError

# DAC full-scale range: -1500 mV .. +1499 mV (MAX5443 output swing).
MV_MIN = -1500
MV_MAX = 1499

# Times are held in a uint16 counter.
TIME_MIN = 1
TIME_MAX = 65535

# Slope / scan rate limits (mV/s).
SLOPE_MIN = 1
SLOPE_MAX = 2000

# Pulse voltammetry limits.  DPV period/width are milliseconds (uint16);
# SWV frequency is in Hz.
STEP_MIN = 1
STEP_MAX = 200
PULSE_MIN = 1
PULSE_MAX = 150
FREQ_MIN = 1
FREQ_MAX = 1000
PERIOD_MIN = 1
PERIOD_MAX = 1000
WIDTH_MIN = 1
WIDTH_MAX = 1000

SCANS_MIN = 1
SCANS_MAX = 255


def _num(params, key, label):
    """Return *key* from *params* as a float, raising InputError if unusable."""
    if key not in params:
        raise InputError(None, f"Missing parameter '{key}' ({label}).")
    try:
        return float(params[key])
    except (TypeError, ValueError):
        raise InputError(params[key], f"{label} must be a number.")


def _check_range(params, key, label, low, high, message=None):
    value = _num(params, key, label)
    if value < low or value > high:
        raise InputError(
            params[key],
            message or f"{label} outside hardware limits ({low}..{high}).",
        )
    return value


def _check_preconditioning(params):
    _check_range(params, "clean_mV", "Clean potential", MV_MIN, MV_MAX,
                 "Clean potential exceeds hardware limits.")
    _check_range(params, "dep_mV", "Deposition potential", MV_MIN, MV_MAX,
                 "Deposition potential exceeds hardware limits.")
    if _num(params, "clean_s", "Clean time") < 0:
        raise InputError(params["clean_s"], "Clean time cannot be negative.")
    if _num(params, "dep_s", "Deposition time") < 0:
        raise InputError(params["dep_s"], "Deposition time cannot be negative.")


def _check_time(params, key="time", label="Time"):
    _check_range(params, key, label, TIME_MIN, TIME_MAX,
                 f"{label} must fit in the 16-bit counter (0..{TIME_MAX}).")


def _validate_cv(params):
    _check_preconditioning(params)
    _check_range(params, "start", "Start", MV_MIN, MV_MAX,
                 "Start parameter exceeds hardware limits.")
    _check_range(params, "slope", "Slope", SLOPE_MIN, SLOPE_MAX,
                 "Slope parameter exceeds hardware limits.")
    _check_range(params, "v1", "Vertex 1", MV_MIN, MV_MAX,
                 "Vertex 1 parameter exceeds hardware limits.")
    _check_range(params, "v2", "Vertex 2", MV_MIN, MV_MAX,
                 "Vertex 2 parameter exceeds hardware limits.")
    _check_range(params, "scans", "Scans", SCANS_MIN, SCANS_MAX,
                 "Scans parameter outside limits.")
    if _num(params, "v1", "Vertex 1") == _num(params, "v2", "Vertex 2"):
        raise InputError(params["v1"], "Vertex 1 cannot equal Vertex 2.")
    if _num(params, "start", "Start") in (
        _num(params, "v1", "Vertex 1"),
        _num(params, "v2", "Vertex 2"),
    ):
        raise InputError(params["start"], "Start cannot equal a vertex.")


def _validate_lsv(params):
    _check_preconditioning(params)
    start = _check_range(params, "start", "Start", MV_MIN, MV_MAX,
                         "Start parameter exceeds hardware limits.")
    stop = _check_range(params, "stop", "Stop", MV_MIN, MV_MAX,
                        "Stop parameter exceeds hardware limits.")
    _check_range(params, "slope", "Slope", SLOPE_MIN, SLOPE_MAX,
                 "Slope parameter exceeds hardware limits.")
    if start == stop:
        raise InputError(params["start"], "Start cannot equal Stop.")


def _validate_sweep(params, frequency_key=None, extra=None):
    """Shared validation for SWV and DPV."""
    _check_preconditioning(params)
    start = _check_range(params, "start", "Start", MV_MIN, MV_MAX,
                         "Start parameter exceeds hardware limits.")
    _check_range(params, "stop", "Stop", MV_MIN, MV_MAX,
                 "Stop parameter exceeds hardware limits.")
    _check_range(params, "step", "Step", STEP_MIN, STEP_MAX,
                 "Step height parameter exceeds hardware limits.")
    _check_range(params, "pulse", "Pulse", PULSE_MIN, PULSE_MAX,
                 "Pulse height parameter exceeds hardware limits.")
    if frequency_key:
        _check_range(params, frequency_key, "Frequency", FREQ_MIN, FREQ_MAX,
                     "Frequency parameter outside limits.")
    if extra:
        extra()
    if start == _num(params, "stop", "Stop"):
        raise InputError(params["start"], "Start cannot equal Stop.")


def _validate_swv(params):
    _validate_sweep(params, frequency_key="freq")


def _validate_dpv(params):
    def _dpv_extra():
        period = _check_range(params, "period", "Pulse period (ms)",
                              PERIOD_MIN, PERIOD_MAX,
                              "Pulse period (ms) parameter outside limits.")
        width = _check_range(params, "width", "Pulse width (ms)",
                             WIDTH_MIN, WIDTH_MAX,
                             "Pulse width (ms) parameter outside limits.")
        if width >= period:
            raise InputError(params["width"], "Width must be less than period.")

    _validate_sweep(params, extra=_dpv_extra)


def _validate_chronoamp(params):
    potentials = params.get("potential") or []
    times = params.get("time") or []
    if not potentials:
        raise InputError(None, "Step table is empty.")
    if len(potentials) != len(times):
        raise InputError(None, "Step table has mismatched potential/time columns.")
    for pot in potentials:
        _check_range({"v": pot}, "v", "Potential", MV_MIN, MV_MAX,
                     "Step potential exceeds hardware limits.")
    for t in times:
        _check_range({"t": t}, "t", "Step time", 0, TIME_MAX,
                     "Step time must fit in the 16-bit counter.")


def _validate_pot(params):
    _check_time(params)


VALIDATORS = {
    "cve": _validate_cv,
    "lsv": _validate_lsv,
    "swv": _validate_swv,
    "dpv": _validate_dpv,
    "cae": _validate_chronoamp,
    "pot": _validate_pot,
}


def validate(exp_id: str, params: dict):
    """Validate *params* for technique *exp_id*.

    Raises InputError with a human-readable message on the first problem
    found.  Unknown techniques are accepted as-is.
    """
    validator = VALIDATORS.get(exp_id)
    if validator is None:
        return
    validator(params)