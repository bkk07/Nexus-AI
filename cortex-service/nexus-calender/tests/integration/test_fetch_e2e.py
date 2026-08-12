from datetime import datetime
from zoneinfo import ZoneInfo

from engine.fetch import CalendarFetchService
from models import (
    CalendarFetchRequest,
    CalendarOperation,
    EventSummary,
)


IST = ZoneInfo("Asia/Kolkata")


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(
        2026,
        8,
        12,
        hour,
        minute,
        tzinfo=IST,
    )


def make_event(
    event_id: str,
    title: str,
    start: datetime,
    end: datetime,
) -> EventSummary:
    return EventSummary(
        event_id=event_id,
        title=title,
        start=start,
        end=end,
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

        if not q:
            return self.events

        return [
            event
            for event in self.events
            if q.lower() in event.title.lower()
        ]

    def get_event(self, event_id: str):
        self.get_event_calls += 1

        for event in self.events:
            if event.event_id == event_id:
                return event

        return None


def test_explicit_id_has_priority_over_search():

    target = make_event(
        "event-target",
        "Project Meeting",
        dt(10),
        dt(11),
    )

    other = make_event(
        "event-other",
        "Project Meeting",
        dt(14),
        dt(15),
    )

    client = FakeCalendarClient(
        [
            target,
            other,
        ]
    )

    service = CalendarFetchService(client)

    request = CalendarFetchRequest(
        operation=CalendarOperation.FETCH,
        event_id="event-target",
        query="Project",
    )

    result = service.fetch(request)

    assert result.status == "found"

    assert result.event is not None

    assert result.event.event_id == "event-target"

    assert client.get_event_calls == 1

    assert client.search_calls == 0


def test_unique_search_result_is_found():

    event = make_event(
        "event-1",
        "Doctor Appointment",
        dt(10),
        dt(11),
    )

    client = FakeCalendarClient(
        [event]
    )

    service = CalendarFetchService(client)

    request = CalendarFetchRequest(
        operation=CalendarOperation.FETCH,
        query="Doctor",
    )

    result = service.fetch(request)

    assert result.status == "found"

    assert result.event is not None

    assert result.event.event_id == "event-1"

    assert result.candidates == []


def test_zero_search_results_are_not_found():

    event = make_event(
        "event-1",
        "DSA Practice",
        dt(10),
        dt(11),
    )

    client = FakeCalendarClient(
        [event]
    )

    service = CalendarFetchService(client)

    request = CalendarFetchRequest(
        operation=CalendarOperation.FETCH,
        query="Gym",
    )

    result = service.fetch(request)

    assert result.status == "not_found"

    assert result.event is None

    assert result.candidates == []


def test_multiple_search_results_are_ambiguous():

    events = [
        make_event(
            "event-1",
            "Team Meeting",
            dt(10),
            dt(11),
        ),
        make_event(
            "event-2",
            "Team Meeting",
            dt(14),
            dt(15),
        ),
    ]

    client = FakeCalendarClient(events)

    service = CalendarFetchService(client)

    request = CalendarFetchRequest(
        operation=CalendarOperation.FETCH,
        query="Team",
    )

    result = service.fetch(request)

    assert result.status == "ambiguous"

    assert result.event is None

    assert result.candidates == events


def test_missing_explicit_id_is_not_found():

    existing = make_event(
        "event-1",
        "Project Work",
        dt(10),
        dt(11),
    )

    client = FakeCalendarClient(
        [existing]
    )

    service = CalendarFetchService(client)

    request = CalendarFetchRequest(
        operation=CalendarOperation.FETCH,
        event_id="missing-event",
    )

    result = service.fetch(request)

    assert result.status == "not_found"

    assert result.event is None

    assert client.get_event_calls == 1

    assert client.search_calls == 0


def test_candidates_are_preserved_for_ambiguous_result():

    first = make_event(
        "event-1",
        "DSA",
        dt(9),
        dt(10),
    )

    second = make_event(
        "event-2",
        "DSA",
        dt(12),
        dt(13),
    )

    third = make_event(
        "event-3",
        "DSA",
        dt(15),
        dt(16),
    )

    events = [
        first,
        second,
        third,
    ]

    client = FakeCalendarClient(events)

    service = CalendarFetchService(client)

    request = CalendarFetchRequest(
        operation=CalendarOperation.FETCH,
        query="DSA",
    )

    result = service.fetch(request)

    assert result.status == "ambiguous"

    assert result.candidates == events

    assert len(result.candidates) == 3