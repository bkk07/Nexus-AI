from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.connectors.calendar.client import CalendarClient


logger = logging.getLogger(__name__)


class CalendarConnector:
    """Application-level Calendar connector."""

    name = "calendar"

    def __init__(
        self,
        calendar_client: CalendarClient,
    ):
        self._client = calendar_client

    async def search(
        self,
        query: str = "",
        time_min: str | None = None,
        time_max: str | None = None,
        top_k: int = 50,
    ) -> list[dict[str, Any]]:

        logger.debug(
            "[CALENDAR_SEARCH] query=%s time_min=%s "
            "time_max=%s top_k=%s",
            query,
            time_min,
            time_max,
            top_k,
        )

        response = await asyncio.to_thread(
            self._client.search_events,
            query=query or None,
            time_min=time_min,
            time_max=time_max,
            max_results=top_k,
        )

        events = response.get("items", [])

        results = [
            self._normalize_event(event)
            for event in events
        ]

        logger.debug(
            "[CALENDAR_SEARCH] result_count=%s",
            len(results),
        )

        return results

    async def fetch(
        self,
        event_id: str,
    ) -> dict[str, Any]:

        logger.debug(
            "[CALENDAR_FETCH] event_id=%s",
            event_id,
        )

        event = await asyncio.to_thread(
            self._client.get_event,
            event_id,
        )

        return self._normalize_event(
            event,
            include_description=True,
        )

    async def count(
        self,
        query: str = "",
        time_min: str | None = None,
        time_max: str | None = None,
    ) -> int:

        logger.debug(
            "[CALENDAR_COUNT] query=%s "
            "time_min=%s time_max=%s",
            query,
            time_min,
            time_max,
        )

        total = 0
        page_token = None

        while True:

            response = await asyncio.to_thread(
                self._client.search_events,
                query=query or None,
                time_min=time_min,
                time_max=time_max,
                max_results=250,
                page_token=page_token,
            )

            total += len(
                response.get("items", [])
            )

            page_token = response.get(
                "nextPageToken"
            )

            if not page_token:
                break

        logger.debug(
            "[CALENDAR_COUNT] total=%s",
            total,
        )

        return total

    async def create(
        self,
        summary: str,
        start: str,
        end: str,
        description: str | None = None,
        location: str | None = None,
        time_zone: str = "Asia/Kolkata",
    ) -> dict[str, Any]:

        event_body: dict[str, Any] = {
            "summary": summary,
            "start": {
                "dateTime": start,
                "timeZone": time_zone,
            },
            "end": {
                "dateTime": end,
                "timeZone": time_zone,
            },
        }

        if description is not None:
            event_body["description"] = description

        if location is not None:
            event_body["location"] = location

        logger.debug(
            "[CALENDAR_CREATE] summary=%s "
            "start=%s end=%s",
            summary,
            start,
            end,
        )

        event = await asyncio.to_thread(
            self._client.create_event,
            event_body,
        )

        return self._normalize_event(
            event,
            include_description=True,
        )

    async def update(
        self,
        event_id: str,
        summary: str | None = None,
        start: str | None = None,
        end: str | None = None,
        description: str | None = None,
        location: str | None = None,
        time_zone: str = "Asia/Kolkata",
    ) -> dict[str, Any]:

        updates: dict[str, Any] = {}

        if summary is not None:
            updates["summary"] = summary

        if description is not None:
            updates["description"] = description

        if location is not None:
            updates["location"] = location

        if start is not None:
            updates["start"] = {
                "dateTime": start,
                "timeZone": time_zone,
            }

        if end is not None:
            updates["end"] = {
                "dateTime": end,
                "timeZone": time_zone,
            }

        if not updates:
            raise ValueError(
                "At least one event field must be "
                "provided for update."
            )

        logger.debug(
            "[CALENDAR_UPDATE] event_id=%s fields=%s",
            event_id,
            list(updates.keys()),
        )

        event = await asyncio.to_thread(
            self._client.update_event,
            event_id,
            updates,
        )

        return self._normalize_event(
            event,
            include_description=True,
        )

    async def delete(
        self,
        event_id: str,
    ) -> dict[str, Any]:

        logger.debug(
            "[CALENDAR_DELETE] event_id=%s",
            event_id,
        )

        await asyncio.to_thread(
            self._client.delete_event,
            event_id,
        )

        return {
            "success": True,
            "event_id": event_id,
        }

    @staticmethod
    def _normalize_event(
        event: dict[str, Any],
        *,
        include_description: bool = True,
    ) -> dict[str, Any]:

        result = {
            "id": event.get("id"),
            "summary": event.get(
                "summary",
                "(No title)",
            ),
            "start": event.get(
                "start",
                {},
            ),
            "end": event.get(
                "end",
                {},
            ),
            "location": event.get(
                "location"
            ),
            "status": event.get(
                "status"
            ),
            "html_link": event.get(
                "htmlLink"
            ),
        }

        if include_description:
            result["description"] = event.get(
                "description"
            )

        return result


def build_default_calendar_connector() -> CalendarConnector:
    return CalendarConnector(
        CalendarClient()
    )