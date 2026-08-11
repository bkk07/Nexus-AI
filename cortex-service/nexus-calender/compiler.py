from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

from datetime_utils import DateTimeNormalizer
from models import CalendarOperation, CalendarRequest


class CalendarQueryCompiler:
    """
    Converts semantic CalendarRequest objects into deterministic
    Google Calendar events.list() query parameters.

    This class does NOT:
        - call Groq
        - call Google Calendar
        - perform network requests

    It only compiles semantic intent into Google Calendar API
    parameters.
    """

    def __init__(
        self,
        default_timezone: str = "Asia/Kolkata",
        default_search_days: int = 30,
    ) -> None:

        if default_search_days <= 0:
            raise ValueError(
                "default_search_days must be positive."
            )

        self.default_timezone = default_timezone
        self.default_search_days = default_search_days

    # =========================================================
    # PUBLIC API
    # =========================================================

    def compile_search(
        self,
        request: CalendarRequest,
        *,
        reference: datetime,
    ) -> dict[str, Any]:
        """
        Compile a SEARCH request into Google Calendar
        events.list() parameters.
        """

        if request.operation != CalendarOperation.SEARCH:
            raise ValueError(
                "compile_search() requires "
                "CalendarOperation.SEARCH."
            )

        timezone = (
            request.timezone
            or self.default_timezone
        )

        normalizer = DateTimeNormalizer(
            timezone=timezone
        )

        # -----------------------------------------------------
        # Determine the base date range.
        # -----------------------------------------------------

        if request.date:

            date_range = (
                normalizer.normalize_date_expression(
                    request.date,
                    reference=reference,
                )
            )

            date_range_start = date_range.start
            date_range_end = date_range.end

        else:
            # No date was specified.
            #
            # We must still create a bounded query.
            #
            # Example:
            #
            # "Find my Nexus AI meetings"
            #
            # Search from the exact reference moment
            # for the configured number of days.
            #
            # Do NOT normalize this to midnight because
            # the user did not request a calendar day.

            reference = normalizer._ensure_timezone(
                reference
            )

            date_range_start = reference

            date_range_end = (
                reference
                + timedelta(
                    days=self.default_search_days
                )
            )

        # -----------------------------------------------------
        # Apply user-requested time range.
        # -----------------------------------------------------

        start, end = self._apply_time_range(
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            start_time=request.start_time,
            end_time=request.end_time,
            timezone=timezone,
        )

        # -----------------------------------------------------
        # Google Calendar events.list() parameters.
        # -----------------------------------------------------

        params: dict[str, Any] = {
            "timeMin": start.isoformat(),
            "timeMax": end.isoformat(),
            "singleEvents": True,
            "orderBy": "startTime",
            "timeZone": timezone,
        }

        if request.query:
            params["q"] = request.query

        return params

    # =========================================================
    # TIME RANGE
    # =========================================================

    def _apply_time_range(
        self,
        *,
        date_range_start: datetime,
        date_range_end: datetime,
        start_time: str | None,
        end_time: str | None,
        timezone: str,
    ) -> tuple[datetime, datetime]:

        # No time restriction.
        if start_time is None and end_time is None:
            return (
                date_range_start,
                date_range_end,
            )

        # A time range requires both boundaries.
        if (
            start_time is None
            or end_time is None
        ):
            raise ValueError(
                "start_time and end_time must "
                "both be provided."
            )

        parsed_start = self._parse_time(
            start_time
        )

        parsed_end = self._parse_time(
            end_time
        )

        # -----------------------------------------------------
        # Normal date expression representing one day.
        #
        # Example:
        #
        # tomorrow
        # 14:00 -> 17:00
        #
        # becomes:
        #
        # tomorrow 14:00
        # tomorrow 17:00
        # -----------------------------------------------------

        if (
            date_range_end - date_range_start
            == timedelta(days=1)
        ):

            start = datetime.combine(
                date_range_start.date(),
                parsed_start,
                tzinfo=date_range_start.tzinfo,
            )

            end = datetime.combine(
                date_range_start.date(),
                parsed_end,
                tzinfo=date_range_start.tzinfo,
            )

            # -------------------------------------------------
            # Overnight range.
            #
            # Example:
            #
            # 12 PM -> 1 AM
            #
            # means:
            #
            # 12 PM today
            # ->
            # 1 AM tomorrow
            # -------------------------------------------------

            if end <= start:
                end += timedelta(days=1)

            return start, end

        # -----------------------------------------------------
        # Multi-day date range.
        #
        # Example:
        #
        # last 7 days
        # 14:00 -> 17:00
        #
        # Apply the time window to the boundaries.
        # -----------------------------------------------------

        start = datetime.combine(
            date_range_start.date(),
            parsed_start,
            tzinfo=date_range_start.tzinfo,
        )

        end = datetime.combine(
            date_range_end.date(),
            parsed_end,
            tzinfo=date_range_end.tzinfo,
        )

        if end <= start:
            raise ValueError(
                "Invalid time range for a multi-day "
                "date expression."
            )

        return start, end

    # =========================================================
    # TIME PARSING
    # =========================================================

    @staticmethod
    def _parse_time(
        value: str,
    ) -> time:

        value = value.strip().upper()

        formats = (
            "%H:%M",
            "%H:%M:%S",
            "%I:%M %p",
            "%I %p",
        )

        for fmt in formats:
            try:
                return datetime.strptime(
                    value,
                    fmt,
                ).time()
            except ValueError:
                continue

        raise ValueError(
            f"Unsupported time format: {value!r}"
        )