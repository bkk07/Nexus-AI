from __future__ import annotations

from datetime import datetime
from typing import Any

from models import CalendarEvent


class CalendarSearchExecutor:
    """
    Executes a compiled Calendar search against Google Calendar.

    This class accepts an already-authenticated Google Calendar
    service object.

    It does NOT:
        - interpret natural language
        - call Groq
        - normalize dates
        - compile queries

    Those responsibilities belong to earlier phases.
    """

    def __init__(
        self,
        service: Any,
        calendar_id: str = "primary",
    ) -> None:

        self.service = service
        self.calendar_id = calendar_id

    # =========================================================
    # PUBLIC API
    # =========================================================

    def search(
        self,
        query: dict[str, Any],
    ) -> list[CalendarEvent]:
        """
        Execute events.list() and normalize the response.
        """

        response = (
            self.service
            .events()
            .list(
                calendarId=self.calendar_id,
                **query,
            )
            .execute()
        )

        raw_events = response.get(
            "items",
            [],
        )

        return [
            self._normalize_event(event)
            for event in raw_events
        ]

    # =========================================================
    # EVENT NORMALIZATION
    # =========================================================

    def _normalize_event(
        self,
        event: dict[str, Any],
    ) -> CalendarEvent:

        start_data = event.get(
            "start",
            {},
        )

        end_data = event.get(
            "end",
            {},
        )

        start_is_all_day = (
            "date" in start_data
        )

        end_is_all_day = (
            "date" in end_data
        )

        start = self._parse_datetime(
            start_data
        )

        end = self._parse_datetime(
            end_data
        )

        return CalendarEvent(
            event_id=event["id"],
            summary=event.get("summary"),
            start=start,
            end=end,
            start_is_all_day=start_is_all_day,
            end_is_all_day=end_is_all_day,
            status=event.get("status"),
            html_link=event.get("htmlLink"),
        )

    @staticmethod
    def _parse_datetime(
        value: dict[str, Any],
    ) -> datetime | None:

        if "dateTime" in value:
            return datetime.fromisoformat(
                value["dateTime"].replace(
                    "Z",
                    "+00:00",
                )
            )

        # All-day events intentionally have no datetime.
        if "date" in value:
            return None

        return None