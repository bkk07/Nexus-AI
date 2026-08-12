from __future__ import annotations

from models import (
    CalendarFetchRequest,
    FetchOutcome,
)


class CalendarFetchService:
    """
    Safely resolves exactly one calendar event.

    Resolution order:

        explicit event_id
                ↓
        direct connector lookup

    otherwise:

        search
          ↓
        0 matches  -> not_found
        1 match    -> found
        >1 matches -> ambiguous

    No event is fabricated.
    No Google API calls are made directly from this service.
    """

    def __init__(
        self,
        client,
    ) -> None:
        self.client = client

    def fetch(
        self,
        request: CalendarFetchRequest,
    ) -> FetchOutcome:
        """
        Resolve one event from a CalendarFetchRequest.
        """

        # -------------------------------------------------
        # 1. Explicit event ID
        # -------------------------------------------------

        if request.event_id is not None:

            event_id = request.event_id.strip()

            if not event_id:
                raise ValueError(
                    "Event ID cannot be empty."
                )

            event = self.client.get_event(
                event_id
            )

            if event is None:
                return FetchOutcome(
                    status="not_found",
                    message=None
                    if False
                    else None,
                )

            return FetchOutcome(
                status="found",
                event=event,
            )

        # -------------------------------------------------
        # 2. Natural-language / search resolution
        # -------------------------------------------------

        query = self._build_search_query(
            request
        )

        candidates = self.client.search(
            query
        )

        # -------------------------------------------------
        # 3. Resolve result count
        # -------------------------------------------------

        if len(candidates) == 0:

            return FetchOutcome(
                status="not_found",
            )

        if len(candidates) == 1:

            return FetchOutcome(
                status="found",
                event=candidates[0],
            )

        return FetchOutcome(
            status="ambiguous",
            candidates=candidates,
        )

    @staticmethod
    def _build_search_query(
        request: CalendarFetchRequest,
    ) -> dict:
        """
        Convert the semantic fetch request into the
        already-supported search query.

        Fetch does not introduce its own fuzzy matching.
        """

        query: dict = {}

        if request.query is not None:
            query["q"] = request.query

        return query