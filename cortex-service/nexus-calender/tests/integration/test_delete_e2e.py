from datetime import datetime
from zoneinfo import ZoneInfo

from engine.delete import CalendarDeleteService
from models import (
    CalendarDeleteRequest,
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

    def __init__(self, events):
        self.events = {
            event.event_id: event
            for event in events
        }

        self.delete_calls = []

    def delete_event(
        self,
        event_id: str,
    ) -> None:

        self.delete_calls.append(event_id)

        if event_id not in self.events:
            raise RuntimeError(
                "Event does not exist."
            )

        del self.events[event_id]


def create_service(events):

    client = FakeCalendarClient(events)

    service = CalendarDeleteService(
        client=client,
    )

    return service, client


# =========================================================
# 1. DELETE BY EXPLICIT ID
# =========================================================

def test_delete_by_explicit_id():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    service, client = create_service([event])

    request = CalendarDeleteRequest(
        operation=CalendarOperation.DELETE,
        event_id="event-1",
    )

    result = service.delete(
        request,
        [event],
    )

    assert result.status == "deleted"

    assert result.event is not None

    assert result.event.event_id == "event-1"

    assert client.delete_calls == [
        "event-1"
    ]

    assert "event-1" not in client.events


# =========================================================
# 2. DELETE BY UNIQUE QUERY
# =========================================================

def test_delete_by_unique_query():

    target = make_event(
        "event-1",
        "Nexus AI",
        dt(17),
        dt(18),
    )

    other = make_event(
        "event-2",
        "DSA",
        dt(10),
        dt(11),
    )

    service, client = create_service(
        [
            target,
            other,
        ]
    )

    request = CalendarDeleteRequest(
        operation=CalendarOperation.DELETE,
        query="Nexus AI",
    )

    result = service.delete(
        request,
        [
            target,
            other,
        ],
    )

    assert result.status == "deleted"

    assert result.event is not None

    assert result.event.event_id == "event-1"

    assert "event-1" not in client.events

    assert "event-2" in client.events


# =========================================================
# 3. MISSING EVENT
# =========================================================

def test_missing_event_returns_not_found():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    service, client = create_service([event])

    request = CalendarDeleteRequest(
        operation=CalendarOperation.DELETE,
        event_id="missing-event",
    )

    result = service.delete(
        request,
        [event],
    )

    assert result.status == "not_found"

    assert result.event is None

    assert client.delete_calls == []

    assert "event-1" in client.events


# =========================================================
# 4. MISSING QUERY
# =========================================================

def test_missing_query_returns_not_found():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    service, client = create_service([event])

    request = CalendarDeleteRequest(
        operation=CalendarOperation.DELETE,
        query="Physics",
    )

    result = service.delete(
        request,
        [event],
    )

    assert result.status == "not_found"

    assert result.event is None

    assert result.candidates == []

    assert client.delete_calls == []


# =========================================================
# 5. AMBIGUOUS QUERY
# =========================================================

def test_ambiguous_query_is_blocked():

    event_1 = make_event(
        "event-1",
        "Meeting",
        dt(10),
        dt(11),
    )

    event_2 = make_event(
        "event-2",
        "Meeting",
        dt(14),
        dt(15),
    )

    service, client = create_service(
        [
            event_1,
            event_2,
        ]
    )

    request = CalendarDeleteRequest(
        operation=CalendarOperation.DELETE,
        query="Meeting",
    )

    result = service.delete(
        request,
        [
            event_1,
            event_2,
        ],
    )

    assert result.status == "ambiguous"

    assert result.event is None

    assert len(result.candidates) == 2

    assert client.delete_calls == []

    assert "event-1" in client.events

    assert "event-2" in client.events


# =========================================================
# 6. CASE INSENSITIVE QUERY
# =========================================================

def test_query_is_case_insensitive():

    event = make_event(
        "event-1",
        "Nexus AI",
        dt(17),
        dt(18),
    )

    service, client = create_service([event])

    request = CalendarDeleteRequest(
        operation=CalendarOperation.DELETE,
        query="nExUs Ai",
    )

    result = service.delete(
        request,
        [event],
    )

    assert result.status == "deleted"

    assert client.delete_calls == [
        "event-1"
    ]


# =========================================================
# 7. SUBSTRING QUERY
# =========================================================

def test_query_matches_title_substring():

    event = make_event(
        "event-1",
        "Nexus AI Project Meeting",
        dt(17),
        dt(18),
    )

    service, client = create_service([event])

    request = CalendarDeleteRequest(
        operation=CalendarOperation.DELETE,
        query="project meeting",
    )

    result = service.delete(
        request,
        [event],
    )

    assert result.status == "deleted"

    assert result.event is not None

    assert result.event.event_id == "event-1"


# =========================================================
# 8. EXPLICIT ID TAKES PRECEDENCE
# =========================================================

def test_explicit_id_takes_precedence():

    event_1 = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    event_2 = make_event(
        "event-2",
        "Project",
        dt(12),
        dt(13),
    )

    service, client = create_service(
        [
            event_1,
            event_2,
        ]
    )

    request = CalendarDeleteRequest(
        operation=CalendarOperation.DELETE,
        event_id="event-1",
        query="Project",
    )

    result = service.delete(
        request,
        [
            event_1,
            event_2,
        ],
    )

    assert result.status == "deleted"

    assert result.event is not None

    assert result.event.event_id == "event-1"

    assert "event-1" not in client.events

    assert "event-2" in client.events


# =========================================================
# 9. ONLY TARGET EVENT IS DELETED
# =========================================================

def test_only_target_event_is_deleted():

    events = [
        make_event(
            "event-1",
            "DSA",
            dt(9),
            dt(10),
        ),
        make_event(
            "event-2",
            "Project",
            dt(12),
            dt(13),
        ),
        make_event(
            "event-3",
            "Meeting",
            dt(14),
            dt(15),
        ),
    ]

    service, client = create_service(events)

    request = CalendarDeleteRequest(
        operation=CalendarOperation.DELETE,
        event_id="event-2",
    )

    result = service.delete(
        request,
        events,
    )

    assert result.status == "deleted"

    assert client.delete_calls == [
        "event-2"
    ]

    assert "event-1" in client.events

    assert "event-2" not in client.events

    assert "event-3" in client.events


# =========================================================
# 10. OVERLAPPING EVENTS DO NOT MATTER
# =========================================================

def test_delete_works_with_overlapping_events():

    event_1 = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(12),
    )

    event_2 = make_event(
        "event-2",
        "Meeting",
        dt(11),
        dt(13),
    )

    service, client = create_service(
        [
            event_1,
            event_2,
        ]
    )

    request = CalendarDeleteRequest(
        operation=CalendarOperation.DELETE,
        event_id="event-1",
    )

    result = service.delete(
        request,
        [
            event_1,
            event_2,
        ],
    )

    assert result.status == "deleted"

    assert "event-1" not in client.events

    assert "event-2" in client.events


# =========================================================
# 11. INVALID OPERATION
# =========================================================

def test_invalid_operation_is_rejected():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    service, client = create_service([event])

    request = CalendarDeleteRequest(
        operation=CalendarOperation.SEARCH,
        event_id="event-1",
    )

    result = service.delete(
        request,
        [event],
    )

    assert result.status == "invalid"

    assert result.event is None

    assert client.delete_calls == []

    assert "event-1" in client.events


# =========================================================
# 12. ZERO DELETE ON AMBIGUITY
# =========================================================

def test_ambiguous_request_performs_zero_deletes():

    events = [
        make_event(
            "event-1",
            "Meeting",
            dt(9),
            dt(10),
        ),
        make_event(
            "event-2",
            "Meeting",
            dt(11),
            dt(12),
        ),
        make_event(
            "event-3",
            "Meeting",
            dt(14),
            dt(15),
        ),
    ]

    service, client = create_service(events)

    request = CalendarDeleteRequest(
        operation=CalendarOperation.DELETE,
        query="Meeting",
    )

    result = service.delete(
        request,
        events,
    )

    assert result.status == "ambiguous"

    assert len(result.candidates) == 3

    assert client.delete_calls == []

    assert len(client.events) == 3


# =========================================================
# 13. RESULT PRESERVES EVENT INFORMATION
# =========================================================

def test_delete_result_contains_original_event():

    event = make_event(
        "event-1",
        "Nexus AI",
        dt(17),
        dt(18),
    )

    service, client = create_service([event])

    result = service.delete(
        CalendarDeleteRequest(
            operation=CalendarOperation.DELETE,
            event_id="event-1",
        ),
        [event],
    )

    assert result.status == "deleted"

    assert result.event is not None

    assert result.event.event_id == "event-1"

    assert result.event.title == "Nexus AI"

    assert result.event.start == dt(17)

    assert result.event.end == dt(18)


# =========================================================
# 14. CONNECTOR FAILURE
# =========================================================

def test_connector_failure_is_not_reported_as_deleted():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    class FailingClient:

        def __init__(self):
            self.delete_calls = []

        def delete_event(self, event_id):

            self.delete_calls.append(
                event_id
            )

            raise RuntimeError(
                "Google Calendar failure"
            )

    client = FailingClient()

    service = CalendarDeleteService(
        client=client,
    )

    request = CalendarDeleteRequest(
        operation=CalendarOperation.DELETE,
        event_id="event-1",
    )

    try:

        service.delete(
            request,
            [event],
        )

        assert False, (
            "Expected deletion failure."
        )

    except RuntimeError as exc:

        assert (
            str(exc)
            == "Calendar event deletion failed."
        )

    assert client.delete_calls == [
        "event-1"
    ]


# =========================================================
# 15. DELETE AFTER QUERY RESOLUTION
# =========================================================

def test_query_resolution_deletes_correct_event():

    target = make_event(
        "event-1",
        "Nexus AI Project",
        dt(17),
        dt(18),
    )

    unrelated = make_event(
        "event-2",
        "DSA Practice",
        dt(10),
        dt(11),
    )

    service, client = create_service(
        [
            target,
            unrelated,
        ]
    )

    request = CalendarDeleteRequest(
        operation=CalendarOperation.DELETE,
        query="Nexus AI",
    )

    result = service.delete(
        request,
        [
            target,
            unrelated,
        ],
    )

    assert result.status == "deleted"

    assert result.event is not None

    assert (
        result.event.event_id
        == "event-1"
    )

    assert client.delete_calls == [
        "event-1"
    ]

    assert "event-1" not in client.events

    assert "event-2" in client.events