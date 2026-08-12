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

    def create_event(
        self,
        event: EventSummary,
    ) -> EventSummary:

        try:

            body = {
                "summary": event.title,

                "start": {
                    "dateTime": event.start.isoformat(),
                    "timeZone": str(
                        event.start.tzinfo
                    ),
                },

                "end": {
                    "dateTime": event.end.isoformat(),
                    "timeZone": str(
                        event.end.tzinfo
                    ),
                },
            }

            if event.location:
                body["location"] = event.location

            if event.description:
                body["description"] = event.description

            response = (
                self.service
                .events()
                .insert(
                    calendarId=self.calendar_id,
                    body=body,
                )
                .execute()
            )

            return self._normalize_event(
                response
            )

        except CalendarConnectorError:
            raise

        except Exception as exc:

            raise CalendarConnectorError(
                "Google Calendar event creation failed.",
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

    def delete_event(
        self,
        event_id: str,
    ) -> None:

        try:

            (
                self.service
                .events()
                .delete(
                    calendarId=self.calendar_id,
                    eventId=event_id,
                )
                .execute()
            )

        except CalendarConnectorError:
            raise

        except Exception as exc:

            raise CalendarConnectorError(
                "Google Calendar event deletion failed.",
                cause=exc,
            ) from exc


    def get_event(
        self,
        event_id: str,
    ) -> EventSummary | None:
        """
        Fetch exactly one Google Calendar event by ID.

        Returns None when the event does not exist.
        """

        if not event_id or not event_id.strip():
            raise CalendarConnectorError(
                "Event ID cannot be empty."
            )

        try:
            response = (
                self.service
                .events()
                .get(
                    calendarId=self.calendar_id,
                    eventId=event_id,
                )
                .execute()
            )

            return self._normalize_event(response)

        except Exception as exc:

            # Google returns HttpError 404 for a missing event.
            status_code = getattr(
                getattr(exc, "resp", None),
                "status",
                None,
            )

            if status_code == 404:
                return None

            raise CalendarConnectorError(
                "Google Calendar event fetch failed.",
                cause=exc,
            ) from exc

    def update_event(
        self,
        event: EventSummary,
    ) -> EventSummary:

        try:

            response = (
                self.service
                .events()
                .update(
                    calendarId=self.calendar_id,
                    eventId=event.event_id,
                    body={
                        "summary": event.title,
                        "description": event.description,
                        "location": event.location,
                        "start": {
                            "dateTime": event.start.isoformat(),
                        },
                        "end": {
                            "dateTime": event.end.isoformat(),
                        },
                    },
                )
                .execute()
            )

            return self._normalize_event(
                response
            )

        except Exception as exc:

            raise CalendarConnectorError(
                "Google Calendar update failed.",
                cause=exc,
            ) from exc

    def delete_event(
        self,
        event_id: str,
    ) -> None:

        try:

            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id,
            ).execute()

        except Exception as exc:

            raise CalendarConnectorError(
                "Google Calendar event deletion failed.",
                cause=exc,
            ) from exc