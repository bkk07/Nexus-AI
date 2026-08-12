from __future__ import annotations

from typing import Any, Protocol

from models import EventSummary

from .errors import CalendarConnectorError


class CalendarClient(Protocol):
    """
    Common interface implemented by both real and fake
    Calendar clients.
    """

    def search(
        self,
        query: dict[str, Any],
    ) -> list[EventSummary]:
        ...

    def create_event(
        self,
        event: EventSummary,
    ) -> EventSummary:
        ...


    def delete_event(
        self,
        event_id: str,
    ) -> None:
        ...
    def get_event(
        self,
        event_id: str,
    ) -> EventSummary | None:
        ...

    def update_event(
        self,
        event: EventSummary,
    ) -> EventSummary:
        ...
    