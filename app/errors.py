"""Framework-independent business failures."""


class BusinessError(Exception):
    """A stable error code and a message suitable for the caller."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
