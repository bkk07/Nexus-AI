from __future__ import annotations

from conflicts import find_conflicts
from datetime_utils import DateTimeRange
from models import (
    AvailabilityOutcome,
    EventSummary,
)


class CalendarAvailabilityService:
    """
    High-level service for checking calendar availability.

    Flow:

        DateTimeRange
              ↓
        conflict detection
              ↓
        AvailabilityOutcome

    This service contains no:
        - Google Calendar API calls
        - LLM calls
        - natural-language interpretation

    The caller is responsible for converting a user's
    natural-language request into a DateTimeRange.
    """

    def check(
        self,
        *,
        window: DateTimeRange,
        existing_events: list[EventSummary],
    ) -> AvailabilityOutcome:
        """
        Check whether the requested time range is available.

        Boundary behavior follows the existing conflict
        engine:

            Event: 10:00 -> 11:00
            Request: 11:00 -> 12:00

        is considered AVAILABLE because touching boundaries
        do not overlap.
        """

        # -------------------------------------------------
        # 1. Validate the requested window
        # -------------------------------------------------

        if window.start.tzinfo is None:
            return AvailabilityOutcome(
                status="invalid",
                conflicts=[],
                message=(
                    "Availability check requires "
                    "a timezone-aware start datetime."
                ),
            )

        if window.end.tzinfo is None:
            return AvailabilityOutcome(
                status="invalid",
                conflicts=[],
                message=(
                    "Availability check requires "
                    "a timezone-aware end datetime."
                ),
            )

        if window.end <= window.start:
            return AvailabilityOutcome(
                status="invalid",
                conflicts=[],
                message=(
                    "Availability window must have "
                    "an end after its start."
                ),
            )

        # -------------------------------------------------
        # 2. Find conflicts
        # -------------------------------------------------

        conflicts = find_conflicts(
            window,
            existing_events,
        )

        # -------------------------------------------------
        # 3. Conflict found
        # -------------------------------------------------

        if conflicts:

            return AvailabilityOutcome(
                status="conflict",
                conflicts=conflicts,
                message=(
                    "The requested time conflicts "
                    "with existing calendar events."
                ),
            )

        # -------------------------------------------------
        # 4. No conflict
        # -------------------------------------------------

        return AvailabilityOutcome(
            status="available",
            conflicts=[],
            message=(
                "The requested time is available."
            ),
        )