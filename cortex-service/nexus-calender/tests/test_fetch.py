from datetime import datetime
from zoneinfo import ZoneInfo

from engine.fetch import CalendarFetchService
from models import (
    CalendarFetchRequest,
    CalendarOperation,
    EventSummary,
)


IST = ZoneInfo("Asia/Kolkata")


def dt(hour: int) -> datetime:
    return datetime(
        2026,
        8,
        12,
        hour,
        0,
        tzinfo=IST,
    )


def make_event(
    event_id: str,
    title: str,
) -> EventSummary:

    return EventSummary(
        event_id=event_id,
        title=title,
        start=dt(10),
        end=dt(11),
    )


class FakeCalendarClient:

    def __init__(
        self,
        events: list[EventSummary],
    ):
        self.events = events
        self.search_calls = 0
        self.get_event_calls = 0

    def search(self, query):
        self.search_calls += 1

        q = query.get("q")

        if q is None:
            return self.events

        return [
            event
            for event in self.events
            if q.lower() in event.title.lower()
        ]

    def get_event(
        self,
        event_id: str,
    ):
        self.get_event_calls += 1

        for event in self.events:

            if event.event_id == event_id:
                return event

        return None


def make_request(
    *,
    event_id=None,
    query=None,
):
    return CalendarFetchRequest(
        operation=CalendarOperation.FETCH,
        event_id=event_id,
        query=query,
    )


def test_explicit_id_fetches_directly():

    event = make_event(
        "event-1",
        "DSA",
    )

    client = FakeCalendarClient(
        [event]
    )

    service = CalendarFetchService(client)

    result = service.fetch(
        make_request(
            event_id="event-1"
        )
    )

    assert result.status == "found"

    assert result.event == event

    # Explicit ID must bypass search.
    assert client.get_event_calls == 1

    assert client.search_calls == 0


def test_unique_search_match_returns_found():

    event = make_event(
        "event-1",
        "DSA Study",
    )

    client = FakeCalendarClient(
        [event]
    )

    service = CalendarFetchService(client)

    result = service.fetch(
        make_request(
            query="DSA"
        )
    )

    assert result.status == "found"

    assert result.event == event


def test_no_search_match_returns_not_found():

    client = FakeCalendarClient([])

    service = CalendarFetchService(client)

    result = service.fetch(
        make_request(
            query="DSA"
        )
    )

    assert result.status == "not_found"

    assert result.event is None

    assert result.candidates == []


def test_multiple_matches_returns_ambiguous():

    event_1 = make_event(
        "event-1",
        "DSA Study",
    )

    event_2 = make_event(
        "event-2",
        "DSA Revision",
    )

    client = FakeCalendarClient(
        [
            event_1,
            event_2,
        ]
    )

    service = CalendarFetchService(client)

    result = service.fetch(
        make_request(
            query="DSA"
        )
    )

    assert result.status == "ambiguous"

    assert result.event is None

    assert result.candidates == [
        event_1,
        event_2,
    ]


def test_explicit_missing_id_returns_not_found():

    client = FakeCalendarClient([])

    service = CalendarFetchService(client)

    result = service.fetch(
        make_request(
            event_id="does-not-exist"
        )
    )

    assert result.status == "not_found"

    assert result.event is None

    # Explicit ID must use direct fetch.
    assert client.get_event_calls == 1

    assert client.search_calls == 0