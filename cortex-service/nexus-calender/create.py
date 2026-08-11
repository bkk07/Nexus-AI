from __future__ import annotations

from datetime import datetime, timezone

from conflicts import find_conflicts
from connector.calendar_client import CalendarClient
from datetime_utils import DateTimeRange
from models import (
    CalendarCreateRequest,
    CreateOutcome,
    EventSummary,
)


class CalendarCreateService:
    """
    Safely creates a calendar event.

    Flow:

        CalendarCreateRequest
                ↓
        duplicate detection
                ↓
        conflict detection
                ↓
        CalendarClient.create_event()

    No Google API calls happen until all safety checks pass.
    """

    def __init__(
        self,
        client: CalendarClient,
        duplicate_tolerance_minutes: int = 0,
    ) -> None:

        if duplicate_tolerance_minutes < 0:
            raise ValueError(
                "duplicate_tolerance_minutes cannot be negative."
            )

        self.client = client
        self.duplicate_tolerance_minutes = (
            duplicate_tolerance_minutes
        )

    def create(
        self,
        request: CalendarCreateRequest,
        existing_events: list[EventSummary],
    ) -> CreateOutcome:
        """
        Safely create an event.

        Duplicate check happens before conflict detection.
        """

        # -----------------------------------------------------
        # 1. Build proposed EventSummary
        # -----------------------------------------------------

        proposed_event = EventSummary(
            event_id="",
            title=request.title,
            start=request.start,
            end=request.end,
            location=request.location,
            description=request.description,
        )

        # -----------------------------------------------------
        # 2. Duplicate detection
        # -----------------------------------------------------

        duplicate = self._find_duplicate(
            proposed_event,
            existing_events,
        )

        if duplicate is not None:

            return CreateOutcome(
                status="duplicate_blocked",
                existing_duplicate=duplicate,
                message=(
                    "An identical calendar event already exists."
                ),
            )

        # -----------------------------------------------------
        # 3. Conflict detection
        # -----------------------------------------------------

        proposed_range = DateTimeRange(
            start=request.start,
            end=request.end,
        )

        conflicts = find_conflicts(
            proposed_range,
            existing_events,
        )

        if conflicts:

            return CreateOutcome(
                status="conflict_blocked",
                conflicts=conflicts,
                message=(
                    "The requested time conflicts "
                    "with existing calendar events."
                ),
            )

        # -----------------------------------------------------
        # 4. Safe to create
        # -----------------------------------------------------

        try:

            created_event = self.client.create_event(
                proposed_event
            )

        except Exception as exc:

            # Do NOT report this as "created".
            raise RuntimeError(
                "Calendar event creation failed."
            ) from exc

        return CreateOutcome(
            status="created",
            event=created_event,
            message="Calendar event created successfully.",
        )

    def _find_duplicate(
        self,
        proposed: EventSummary,
        existing_events: list[EventSummary],
    ) -> EventSummary | None:
        """
        Find an exact duplicate.

        Duplicate policy:

        - title must match after normalization
        - start must match
        - end must match

        By default tolerance is zero minutes.
        """

        normalized_title = self._normalize_title(
            proposed.title
        )

        for existing in existing_events:

            if (
                self._normalize_title(existing.title)
                != normalized_title
            ):
                continue

            if not self._times_match(
                proposed.start,
                existing.start,
            ):
                continue

            if not self._times_match(
                proposed.end,
                existing.end,
            ):
                continue

            return existing

        return None

    def _times_match(
        self,
        first: datetime,
        second: datetime,
    ) -> bool:
        """
        Compare two timezone-aware datetimes.

        Equivalent timezone representations are compared
        using UTC.
        """

        if (
            first.tzinfo is None
            or second.tzinfo is None
        ):
            raise ValueError(
                "Duplicate comparison requires "
                "timezone-aware datetimes."
            )

        difference = abs(
            (
                first.astimezone(timezone.utc)
                - second.astimezone(timezone.utc)
            ).total_seconds()
        )

        return difference <= (
            self.duplicate_tolerance_minutes * 60
        )

    @staticmethod
    def _normalize_title(
        title: str,
    ) -> str:
        """
        Normalize title for duplicate comparison.

        Case-insensitive + whitespace-normalized.
        """

        return " ".join(
            title.strip().lower().split()
        )