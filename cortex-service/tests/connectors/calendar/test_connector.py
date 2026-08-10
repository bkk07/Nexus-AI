from __future__ import annotations

import asyncio

import pytest

from app.connectors.calendar.connector import CalendarConnector


# ============================================================
# Fake Calendar Client
# ============================================================

class FakeCalendarClient:

    def __init__(self):
        self.events = {
            "event-1": {
                "id": "event-1",
                "summary": "DSA Practice",
                "description": "Practice graphs and DP.",
                "location": "Library",
                "start": {
                    "dateTime": "2026-08-10T14:00:00+05:30",
                    "timeZone": "Asia/Kolkata",
                },
                "end": {
                    "dateTime": "2026-08-10T15:00:00+05:30",
                    "timeZone": "Asia/Kolkata",
                },
                "status": "confirmed",
                "htmlLink": "https://calendar.google.com/",
            },
            "event-2": {
                "id": "event-2",
                "summary": "Nexus AI Development",
                "description": "Calendar integration.",
                "location": "Home",
                "start": {
                    "dateTime": "2026-08-10T16:00:00+05:30",
                    "timeZone": "Asia/Kolkata",
                },
                "end": {
                    "dateTime": "2026-08-10T17:30:00+05:30",
                    "timeZone": "Asia/Kolkata",
                },
                "status": "confirmed",
                "htmlLink": "https://calendar.google.com/",
            },
            "event-3": {
                "id": "event-3",
                "summary": "Placement Preparation",
                "description": "OS, DBMS and CNS preparation.",
                "location": None,
                "start": {
                    "dateTime": "2026-08-10T19:00:00+05:30",
                    "timeZone": "Asia/Kolkata",
                },
                "end": {
                    "dateTime": "2026-08-10T20:00:00+05:30",
                    "timeZone": "Asia/Kolkata",
                },
                "status": "confirmed",
                "htmlLink": "https://calendar.google.com/",
            },
            "event-4": {
                "id": "event-4",
                "summary": "Nexus AI Review",
                "description": "Review today's implementation.",
                "location": None,
                "start": {
                    "dateTime": "2026-08-10T21:00:00+05:30",
                    "timeZone": "Asia/Kolkata",
                },
                "end": {
                    "dateTime": "2026-08-10T21:45:00+05:30",
                    "timeZone": "Asia/Kolkata",
                },
                "status": "confirmed",
                "htmlLink": "https://calendar.google.com/",
            },
        }

    # ========================================================
    # SEARCH
    # ========================================================

    def search_events(
        self,
        *,
        query=None,
        time_min=None,
        time_max=None,
        max_results=50,
        page_token=None,
    ):
        values = list(self.events.values())

        if query:
            q = query.lower()

            values = [
                event
                for event in values
                if (
                    q
                    in event.get(
                        "summary",
                        "",
                    ).lower()
                    or
                    q
                    in event.get(
                        "description",
                        "",
                    ).lower()
                )
            ]

        # Match the real Google Calendar API response shape.
        return {
            "items": values[:max_results],
        }

    # ========================================================
    # FETCH
    # ========================================================

    def get_event(self, event_id):
        if event_id not in self.events:
            raise KeyError(event_id)

        return self.events[event_id]

    # ========================================================
    # CREATE
    # ========================================================

    def create_event(self, event):

        event_id = f"event-{len(self.events) + 1}"

        created_event = {
            **event,
            "id": event_id,
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/",
        }

        self.events[event_id] = created_event

        return created_event

    # ========================================================
    # UPDATE
    # ========================================================

    def update_event(
        self,
        event_id,
        event,
    ):
        if event_id not in self.events:
            raise KeyError(event_id)

        updated_event = {
            **self.events[event_id],
            **event,
            "id": event_id,
        }

        self.events[event_id] = updated_event

        return updated_event

    # ========================================================
    # DELETE
    # ========================================================

    def delete_event(self, event_id):

        if event_id not in self.events:
            raise KeyError(event_id)

        del self.events[event_id]


# ============================================================
# Helper
# ============================================================

def make_connector():

    return CalendarConnector(
        FakeCalendarClient()
    )


# ============================================================
# SEARCH TESTS
# ============================================================

def test_calendar_search():

    connector = make_connector()

    results = asyncio.run(
        connector.search(
            time_min="2026-08-10T12:00:00+05:30",
            time_max="2026-08-10T23:59:59+05:30",
            top_k=50,
        )
    )

    assert len(results) == 4

    assert results[0]["id"] == "event-1"
    assert results[0]["summary"] == "DSA Practice"

    assert results[1]["id"] == "event-2"
    assert (
        results[1]["summary"]
        == "Nexus AI Development"
    )

    assert results[2]["id"] == "event-3"
    assert (
        results[2]["summary"]
        == "Placement Preparation"
    )

    assert results[3]["id"] == "event-4"
    assert (
        results[3]["summary"]
        == "Nexus AI Review"
    )


def test_calendar_search_with_query():

    class QueryCheckingClient(FakeCalendarClient):

        def search_events(
            self,
            *,
            query=None,
            time_min=None,
            time_max=None,
            max_results=50,
            page_token=None,
        ):
            assert query == "Nexus AI"

            return {
                "items": [
                    self.events["event-2"],
                    self.events["event-4"],
                ]
            }

    connector = CalendarConnector(
        QueryCheckingClient()
    )

    results = asyncio.run(
        connector.search(
            query="Nexus AI",
            top_k=10,
        )
    )

    assert len(results) == 2

    summaries = {
        event["summary"]
        for event in results
    }

    assert summaries == {
        "Nexus AI Development",
        "Nexus AI Review",
    }


# ============================================================
# FETCH TEST
# ============================================================

def test_calendar_fetch():

    connector = make_connector()

    result = asyncio.run(
        connector.fetch(
            "event-2"
        )
    )

    assert result["id"] == "event-2"

    assert (
        result["summary"]
        == "Nexus AI Development"
    )

    assert (
        result["description"]
        == "Calendar integration."
    )

    assert result["location"] == "Home"

    assert result["status"] == "confirmed"


# ============================================================
# COUNT TEST
# ============================================================

def test_calendar_count():

    connector = make_connector()

    count = asyncio.run(
        connector.count(
            query="Nexus AI"
        )
    )

    assert count == 2


def test_calendar_count_all():

    connector = make_connector()

    count = asyncio.run(
        connector.count()
    )

    assert count == 4


# ============================================================
# CREATE TEST
# ============================================================

def test_calendar_create():

    connector = make_connector()

    result = asyncio.run(
        connector.create(
            summary="Interview Preparation",
            start=(
                "2026-08-10T22:00:00+05:30"
            ),
            end=(
                "2026-08-10T23:00:00+05:30"
            ),
            description=(
                "Prepare for technical interview."
            ),
            location="Online",
        )
    )

    assert result["id"] == "event-5"

    assert (
        result["summary"]
        == "Interview Preparation"
    )

    assert (
        result["description"]
        == "Prepare for technical interview."
    )

    assert result["location"] == "Online"

    assert result["status"] == "confirmed"


# ============================================================
# UPDATE TEST
# ============================================================

def test_calendar_update():

    connector = make_connector()

    result = asyncio.run(
        connector.update(
            event_id="event-2",
            summary="Nexus AI Updated",
            start=(
                "2026-08-10T18:00:00+05:30"
            ),
            end=(
                "2026-08-10T19:00:00+05:30"
            ),
        )
    )

    assert result["id"] == "event-2"

    assert (
        result["summary"]
        == "Nexus AI Updated"
    )

    assert (
        result["start"]["dateTime"]
        == "2026-08-10T18:00:00+05:30"
    )

    assert (
        result["end"]["dateTime"]
        == "2026-08-10T19:00:00+05:30"
    )


def test_calendar_update_requires_field():

    connector = make_connector()

    with pytest.raises(ValueError):

        asyncio.run(
            connector.update(
                event_id="event-2"
            )
        )


# ============================================================
# DELETE TEST
# ============================================================

def test_calendar_delete():

    client = FakeCalendarClient()

    connector = CalendarConnector(client)

    result = asyncio.run(
        connector.delete(
            "event-4"
        )
    )
    assert result == {
        "success": True,
        "event_id": "event-4",
    }

    assert "event-4" not in client.events