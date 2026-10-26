"""Custom exception types for dstat-interface."""


class InputError(Exception):
    """Raised when invalid user input is detected."""
    pass


class VarError(Exception):
    """Raised when an internal variable has an unexpected value."""
    pass
