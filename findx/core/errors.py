"""Exception types shared by all engines."""


class FindxError(Exception):
    """Base class for user-facing errors."""


class InputError(FindxError):
    """The user's input is malformed or unsupported."""


class ComputationError(FindxError):
    """The input was valid but no result could be computed reliably."""
