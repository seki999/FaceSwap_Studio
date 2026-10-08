class StudioError(Exception):
    """A user-facing application failure."""

class Cancelled(StudioError):
    pass
