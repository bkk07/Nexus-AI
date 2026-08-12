from __future__ import annotations

from models import (
    CalendarDeleteRequest,
    CalendarOperation,
    DeleteOutcome,
    EventSummary,
)

from connector.calendar_client import CalendarClient


class CalendarDeleteService:
    """
    Safely deletes a calendar event.

    Flow:

        CalendarDeleteRequest
                ↓
        resolve target event
                ↓
        missing / ambiguous check
                ↓
        CalendarClient.delete_event()
                ↓
        DeleteOutcome

    No Google Calendar deletion happens unless
    exactly one event has been resolved.
    """

    def __init__(
        self,
        client: CalendarClient,
    ) -> None:

        self.client = client

    def delete(
        self,
        request: CalendarDeleteRequest,
        existing_events: list[EventSummary],
    ) -> DeleteOutcome:
        """
        Safely delete a single calendar event.
        """

        # -------------------------------------------------
        # 1. Validate operation
        # -------------------------------------------------

        if request.operation != CalendarOperation.DELETE:

            return DeleteOutcome(
                status="invalid",
                message=(
                    "CalendarDeleteService only "
                    "supports DELETE."
                ),
            )

        # -------------------------------------------------
        # 2. Resolve event
        # -------------------------------------------------

        event = self._resolve_event(
            request,
            existing_events,
        )

        # -------------------------------------------------
        # 3. Resolution failed
        # -------------------------------------------------

        if event is None:

            candidates = self._find_candidates(
                request,
                existing_events,
            )

            if len(candidates) > 1:

                return DeleteOutcome(
                    status="ambiguous",
                    candidates=candidates,
                    message=(
                        "Multiple calendar events "
                        "match the request."
                    ),
                )

            return DeleteOutcome(
                status="not_found",
                message=(
                    "No matching calendar event "
                    "was found."
                ),
            )

        # -------------------------------------------------
        # 4. Safe to delete
        # -------------------------------------------------

        try:

            self.client.delete_event(
                event.event_id
            )

        except Exception as exc:

            # Never report deletion as successful
            # if the connector failed.
            raise RuntimeError(
                "Calendar event deletion failed."
            ) from exc

        return DeleteOutcome(
            status="deleted",
            event=event,
            message=(
                "Calendar event deleted successfully."
            ),
        )

    # =====================================================
    # EVENT RESOLUTION
    # =====================================================

    def _resolve_event(
        self,
        request: CalendarDeleteRequest,
        existing_events: list[EventSummary],
    ) -> EventSummary | None:

        # -------------------------------------------------
        # Explicit event ID
        # -------------------------------------------------

        if request.event_id:

            for event in existing_events:

                if (
                    event.event_id
                    == request.event_id
                ):

                    return event

            return None

        # -------------------------------------------------
        # Natural-language / title query
        # -------------------------------------------------

        candidates = self._find_candidates(
            request,
            existing_events,
        )

        if len(candidates) == 1:

            return candidates[0]

        return None

    # =====================================================
    # FIND MATCHING EVENTS
    # =====================================================

    def _find_candidates(
        self,
        request: CalendarDeleteRequest,
        existing_events: list[EventSummary],
    ) -> list[EventSummary]:

        if not request.query:

            return []

        normalized_query = (
            request.query
            .strip()
            .lower()
        )

        if not normalized_query:

            return []

        return [
            event
            for event in existing_events
            if normalized_query
            in event.title.strip().lower()
        ]