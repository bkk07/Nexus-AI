from __future__ import annotations

from conflicts import find_conflicts
from connector.calendar_client import CalendarClient
from datetime_utils import DateTimeRange
from models import (
    CalendarOperation,
    CalendarUpdateRequest,
    EventSummary,
    UpdateOutcome,
)


class CalendarUpdateService:
    """
    Safely updates exactly one calendar event.

    Flow:

        CalendarUpdateRequest
                ↓
        Resolve exactly one event
                ↓
        Build proposed event
                ↓
        If time changed:
            conflict detection
            excluding current event
                ↓
        CalendarClient.update_event()
                ↓
        UpdateOutcome

    No write occurs until every safety check passes.
    """

    def __init__(
        self,
        client: CalendarClient,
    ) -> None:

        self.client = client

    def update(
        self,
        request: CalendarUpdateRequest,
        existing_events: list[EventSummary],
    ) -> UpdateOutcome:

        if request.operation != CalendarOperation.UPDATE:
            return UpdateOutcome(
                status="invalid",
                message=(
                    "CalendarUpdateService only "
                    "supports UPDATE."
                ),
            )

        # -------------------------------------------------
        # 1. Resolve target event
        # -------------------------------------------------

        resolution = self._resolve_event(
            request,
            existing_events,
        )

        if resolution is None:

            return UpdateOutcome(
                status="not_found",
                message="Calendar event was not found.",
            )

        if isinstance(resolution, list):

            return UpdateOutcome(
                status="ambiguous",
                candidates=resolution,
                message=(
                    "Multiple calendar events match "
                    "the requested event."
                ),
            )

        existing_event = resolution

        # -------------------------------------------------
        # 2. Build proposed event
        # -------------------------------------------------

        proposed_event = EventSummary(
            event_id=existing_event.event_id,
            title=(
                request.new_title
                if request.new_title is not None
                else existing_event.title
            ),
            start=(
                request.new_start
                if request.new_start is not None
                else existing_event.start
            ),
            end=(
                request.new_end
                if request.new_end is not None
                else existing_event.end
            ),
            location=(
                request.new_location
                if request.new_location is not None
                else existing_event.location
            ),
            description=(
                request.new_description
                if request.new_description is not None
                else existing_event.description
            ),
        )

        # -------------------------------------------------
        # 3. Validate datetime range
        # -------------------------------------------------

        if proposed_event.end <= proposed_event.start:

            return UpdateOutcome(
                status="invalid",
                message=(
                    "Updated event end must be "
                    "after its start."
                ),
            )

        # -------------------------------------------------
        # 4. Detect whether time changed
        # -------------------------------------------------

        time_changed = (
            proposed_event.start
            != existing_event.start
            or
            proposed_event.end
            != existing_event.end
        )

        # -------------------------------------------------
        # 5. Conflict check only if time changed
        # -------------------------------------------------

        if time_changed:

            other_events = [
                event
                for event in existing_events
                if event.event_id
                != existing_event.event_id
            ]

            proposed_range = DateTimeRange(
                start=proposed_event.start,
                end=proposed_event.end,
            )

            conflicts = find_conflicts(
                proposed_range,
                other_events,
            )

            if conflicts:

                return UpdateOutcome(
                    status="conflict_blocked",
                    conflicts=conflicts,
                    message=(
                        "The updated time conflicts "
                        "with existing calendar events."
                    ),
                )

        # -------------------------------------------------
        # 6. Safe to update
        # -------------------------------------------------

        try:

            updated_event = (
                self.client.update_event(
                    proposed_event
                )
            )

        except Exception as exc:

            raise RuntimeError(
                "Calendar event update failed."
            ) from exc

        return UpdateOutcome(
            status="updated",
            event=updated_event,
            message=(
                "Calendar event updated successfully."
            ),
        )

    @staticmethod
    def _resolve_event(
        request: CalendarUpdateRequest,
        events: list[EventSummary],
    ) -> EventSummary | list[EventSummary] | None:

        # Explicit ID has priority.

        if request.event_id is not None:

            for event in events:

                if event.event_id == request.event_id:
                    return event

            return None

        # No ID → query-based resolution.

        if request.query is not None:

            normalized_query = (
                request.query.strip().lower()
            )

            matches = [
                event
                for event in events
                if normalized_query
                in event.title.lower()
            ]

            if not matches:
                return None

            if len(matches) > 1:
                return matches

            return matches[0]

        return None