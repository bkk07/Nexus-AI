from __future__ import annotations

from typing import Any

from googleapiclient.discovery import build

from models import EventSummary

from .errors import CalendarConnectorError
from .google_auth import get_google_calendar_credentials


class GoogleCalendarClient:
    """
    Real Google Calendar implementation.

    This is intentionally a thin connector layer.
    """

    def __init__(
        self,
        calendar_id: str = "primary",
    ) -> None:

        self.calendar_id = calendar_id

        try:
            credentials = (
                get_google_calendar_credentials()
            )

            self.service = build(
                "calendar",
                "v3",
                credentials=credentials,
                cache_discovery=False,
            )

        except Exception as exc:

            raise CalendarConnectorError(
                "Failed to initialize Google Calendar.",
                cause=exc,
            ) from exc

    def search(
        self,
        query: dict[str, Any],
    ) -> list[EventSummary]:

        try:

            events: list[EventSummary] = []

            page_token: str | None = None

            while True:

                params = {
                    "calendarId": self.calendar_id,
                    **query,
                }

                if page_token:
                    params["pageToken"] = page_token

                response = (
                    self.service
                    .events()
                    .list(**params)
                    .execute()
                )

                for raw_event in response.get(
                    "items",
                    [],
                ):

                    events.append(
                        self._normalize_event(
                            raw_event
                        )
                    )

                page_token = response.get(
                    "nextPageToken"
                )

                if not page_token:
                    break

            return events

        except CalendarConnectorError:
            raise

        except Exception as exc:

            raise CalendarConnectorError(
                "Google Calendar search failed.",
                cause=exc,
            ) from exc

    @staticmethod
    def _normalize_event(
        event: dict[str, Any],
    ) -> EventSummary:

        if "id" not in event:
            raise CalendarConnectorError(
                "Google Calendar event has no ID."
            )

        start_data = event.get(
            "start",
            {},
        )

        end_data = event.get(
            "end",
            {},
        )

        start = (
            GoogleCalendarClient
            ._parse_datetime(start_data)
        )

        end = (
            GoogleCalendarClient
            ._parse_datetime(end_data)
        )

        if start is None or end is None:
            raise CalendarConnectorError(
                "Google Calendar event has "
                "invalid start/end."
            )

        return EventSummary(
            event_id=event["id"],
            title=event.get(
                "summary",
                "",
            ),
            start=start,
            end=end,
            location=event.get(
                "location"
            ),
            description=event.get(
                "description"
            ),
        )

    @staticmethod
    def _parse_datetime(
        value: dict[str, Any],
    ):
        from datetime import datetime

        if "dateTime" in value:

            return datetime.fromisoformat(
                value["dateTime"].replace(
                    "Z",
                    "+00:00",
                )
            )

        # Google all-day events contain "date".
        #
        # Phase 5 EventSummary requires datetime,
        # so represent the date boundary at midnight UTC.
        if "date" in value:

            return datetime.fromisoformat(
                value["date"]
                + "T00:00:00+00:00"
            )

        return None