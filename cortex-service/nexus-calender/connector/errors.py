class CalendarConnectorError(Exception):
    """
    Typed error raised when the Calendar connector fails.

    Connector-specific exceptions must not leak through the
    Calendar engine.
    """

    def __init__(
        self,
        message: str,
        *,
        cause: Exception | None = None,
    ) -> None:

        super().__init__(message)

        self.cause = cause