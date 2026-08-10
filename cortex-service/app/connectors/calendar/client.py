from __future__ import annotations

import os
from typing import Any

CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"


class CalendarClient:
    """Thin wrapper around the Google Calendar v3 API."""

    def __init__(self) -> None:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")

        missing = [
            name
            for name, value in {
                "GOOGLE_CLIENT_ID": client_id,
                "GOOGLE_CLIENT_SECRET": client_secret,
                "GOOGLE_REFRESH_TOKEN": refresh_token,
            }.items()
            if not value
        ]

        if missing:
            raise ValueError(
                "Missing Google Calendar OAuth environment variables: "
                + ", ".join(missing)
            )

        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=[CALENDAR_SCOPE],
        )

        self._service = build(
            "calendar",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

    def search_events(
        self,
        *,
        query: str | None = None,
        time_min: str | None = None,
        time_max: str | None = None,
        max_results: int = 50,
        page_token: str | None = None,
    ) -> dict[str, Any]:

        params: dict[str, Any] = {
            "calendarId": "primary",
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }

        if query:
            params["q"] = query

        if time_min:
            params["timeMin"] = time_min

        if time_max:
            params["timeMax"] = time_max

        if page_token:
            params["pageToken"] = page_token

        return (
            self._service.events()
            .list(**params)
            .execute(num_retries=3)
        )

    def get_event(
        self,
        event_id: str,
    ) -> dict[str, Any]:

        return (
            self._service.events()
            .get(
                calendarId="primary",
                eventId=event_id,
            )
            .execute(num_retries=3)
        )

    def create_event(
        self,
        event: dict[str, Any],
    ) -> dict[str, Any]:

        return (
            self._service.events()
            .insert(
                calendarId="primary",
                body=event,
            )
            .execute(num_retries=3)
        )

    def update_event(
        self,
        event_id: str,
        event: dict[str, Any],
    ) -> dict[str, Any]:

        return (
            self._service.events()
            .patch(
                calendarId="primary",
                eventId=event_id,
                body=event,
            )
            .execute(num_retries=3)
        )

    def delete_event(
        self,
        event_id: str,
    ) -> None:

        (
            self._service.events()
            .delete(
                calendarId="primary",
                eventId=event_id,
            )
            .execute(num_retries=3)
        )