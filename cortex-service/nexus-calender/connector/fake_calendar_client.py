from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from models import EventSummary

from .errors import CalendarConnectorError


class FakeCalendarClient:
    """
    Deterministic in-memory Calendar client.

    Used for:
        - unit tests
        - integration tests
        - demos

    Never performs network requests.
    """

    def __init__(
        self,
        events: Iterable[EventSummary],
    ) -> None:

        self._events = list(events)

        self.search_calls: list[
            dict[str, Any]
        ] = []

    def search(
        self,
        query: dict[str, Any],
    ) -> list[EventSummary]:

        self.search_calls.append(
            dict(query)
        )

        try:
            return self._search(
                query
            )

        except CalendarConnectorError:
            raise

        except Exception as exc:
            raise CalendarConnectorError(
                "Fake Calendar search failed.",
                cause=exc,
            ) from exc

    def _search(
        self,
        query: dict[str, Any],
    ) -> list[EventSummary]:

        time_min = self._parse_query_time(
            query.get("timeMin")
        )

        time_max = self._parse_query_time(
            query.get("timeMax")
        )

        text_query = query.get("q")

        if time_min is None or time_max is None:
            raise CalendarConnectorError(
                "Fake Calendar requires timeMin and timeMax."
            )

        results: list[EventSummary] = []

        for event in self._events:

            # ---------------------------------------------
            # Time overlap
            #
            # Event overlaps [timeMin, timeMax)
            # iff:
            #
            # event.start < timeMax
            # AND
            # event.end > timeMin
            # ---------------------------------------------

            if not (
                event.start < time_max
                and event.end > time_min
            ):
                continue

            # ---------------------------------------------
            # Text filtering
            # ---------------------------------------------

            if text_query:

                if not self._matches_text(
                    event,
                    text_query,
                ):
                    continue

            results.append(event)

        results.sort(
            key=lambda event: event.start
        )

        return results

    @staticmethod
    def _matches_text(
        event: EventSummary,
        query: str,
    ) -> bool:

        query = query.strip().lower()

        if not query:
            return True

        searchable = " ".join(
            [
                event.title or "",
                event.location or "",
                event.description or "",
            ]
        ).lower()

        return query in searchable

    @staticmethod
    def _parse_query_time(
        value: str | None,
    ) -> datetime | None:

        if value is None:
            return None

        try:
            return datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                )
            )

        except ValueError as exc:
            raise CalendarConnectorError(
                f"Invalid Calendar query timestamp: {value!r}",
                cause=exc,
            ) from exc