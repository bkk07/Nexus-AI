from __future__ import annotations

from datetime import datetime

from availability import (
    AvailabilityResult,
    check_availability,
)
from busy_intervals import BusyInterval
from compiler import CalendarQueryCompiler
from datetime_utils import DateTimeRange, DateTimeNormalizer
from models import CalendarOperation, CalendarRequest


class AvailabilityService:
    """
    Converts a semantic CHECK_AVAILABILITY request into
    a deterministic availability result.

    This service does NOT:
        - call Groq
        - call Google Calendar
        - perform natural-language parsing

    It:
        1. validates the CalendarRequest
        2. normalizes the date
        3. applies the requested time range
        4. checks the range against busy intervals
    """

    def __init__(
        self,
        default_timezone: str = "Asia/Kolkata",
    ) -> None:
        self.default_timezone = default_timezone

    def check(
        self,
        request: CalendarRequest,
        busy_intervals: list[BusyInterval],
        *,
        reference: datetime,
    ) -> AvailabilityResult:

        if request.operation != (
            CalendarOperation.CHECK_AVAILABILITY
        ):
            raise ValueError(
                "AvailabilityService requires "
                "CalendarOperation.CHECK_AVAILABILITY."
            )

        if not request.date:
            raise ValueError(
                "CHECK_AVAILABILITY requires a date."
            )

        if not request.start_time:
            raise ValueError(
                "CHECK_AVAILABILITY requires start_time."
            )

        if not request.end_time:
            raise ValueError(
                "CHECK_AVAILABILITY requires end_time."
            )

        timezone = (
            request.timezone
            or self.default_timezone
        )

        normalizer = DateTimeNormalizer(
            timezone=timezone
        )

        date_range = (
            normalizer.normalize_date_expression(
                request.date,
                reference=reference,
            )
        )

        # CalendarQueryCompiler already contains the
        # tested time-range logic from Phase 4.
        compiler = CalendarQueryCompiler(
            default_timezone=timezone
        )

        start, end = compiler._apply_time_range(
            date_range_start=date_range.start,
            date_range_end=date_range.end,
            start_time=request.start_time,
            end_time=request.end_time,
            timezone=timezone,
        )

        # IMPORTANT:
        # _apply_time_range() returns a tuple:
        #
        #     (start, end)
        #
        # Availability checking expects our application's
        # DateTimeRange object.
        requested_range = DateTimeRange(
            start=start,
            end=end,
        )

        return check_availability(
            requested_range,
            busy_intervals,
        )