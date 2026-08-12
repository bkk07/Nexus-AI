from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from engine.update import CalendarUpdateService
from models import (
    CalendarOperation,
    CalendarUpdateRequest,
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


class FakeCalendarClient:

    def __init__(self, events):
        self.events = {
            event.event_id: event
            for event in events
        }

        self.update_calls = []

    def update_event(
        self,
        event: EventSummary,
    ) -> EventSummary:

        self.update_calls.append(event)

        if event.event_id not in self.events:
            raise RuntimeError(
                "Event does not exist."
            )

        self.events[event.event_id] = event

        return event


def make_event(
    event_id: str,
    title: str,
    start: datetime,
    end: datetime,
    location: str | None = None,
    description: str | None = None,
) -> EventSummary:

    return EventSummary(
        event_id=event_id,
        title=title,
        start=start,
        end=end,
        location=location,
        description=description,
    )


def make_service(events):

    client = FakeCalendarClient(events)

    service = CalendarUpdateService(
        client=client,
    )

    return service, client


# =========================================================
# 1. UPDATE TITLE ONLY
# =========================================================

def test_update_title_only():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    service, client = make_service(
        [event]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_title="Advanced DSA",
    )

    result = service.update(
        request,
        [event],
    )

    assert result.status == "updated"

    assert result.event is not None

    assert result.event.title == "Advanced DSA"

    assert result.event.start == dt(10)

    assert result.event.end == dt(11)

    assert len(client.update_calls) == 1


# =========================================================
# 2. UPDATE START TIME
# =========================================================

def test_update_start_time():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    service, client = make_service(
        [event]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_start=dt(12),
        new_end=dt(13),
    )

    result = service.update(
        request,
        [event],
    )

    assert result.status == "updated"

    assert result.event is not None

    assert result.event.start == dt(12)

    assert result.event.end == dt(13)

    assert len(client.update_calls) == 1


# =========================================================
# 3. UPDATE END TIME
# =========================================================

def test_update_end_time():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    service, client = make_service(
        [event]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_end=dt(12),
    )

    result = service.update(
        request,
        [event],
    )

    assert result.status == "updated"

    assert result.event is not None

    assert result.event.start == dt(10)

    assert result.event.end == dt(12)

    assert len(client.update_calls) == 1


# =========================================================
# 4. UPDATE DESCRIPTION ONLY
# =========================================================

def test_update_description_only():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
        description="Old description",
    )

    service, client = make_service(
        [event]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_description="New description",
    )

    result = service.update(
        request,
        [event],
    )

    assert result.status == "updated"

    assert result.event is not None

    assert (
        result.event.description
        == "New description"
    )

    assert result.event.start == dt(10)

    assert result.event.end == dt(11)

    assert len(client.update_calls) == 1


# =========================================================
# 5. UPDATE LOCATION ONLY
# =========================================================

def test_update_location_only():

    event = make_event(
        "event-1",
        "Meeting",
        dt(10),
        dt(11),
        location="Old Room",
    )

    service, client = make_service(
        [event]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_location="New Room",
    )

    result = service.update(
        request,
        [event],
    )

    assert result.status == "updated"

    assert result.event is not None

    assert (
        result.event.location
        == "New Room"
    )

    assert len(client.update_calls) == 1


# =========================================================
# 6. MULTIPLE FIELDS AT ONCE
# =========================================================

def test_update_multiple_fields_atomically():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
        location="Room A",
        description="Old",
    )

    service, client = make_service(
        [event]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_title="Advanced DSA",
        new_start=dt(14),
        new_end=dt(16),
        new_location="Room B",
        new_description="Updated description",
    )

    result = service.update(
        request,
        [event],
    )

    assert result.status == "updated"

    assert result.event is not None

    updated = result.event

    assert updated.title == "Advanced DSA"

    assert updated.start == dt(14)

    assert updated.end == dt(16)

    assert updated.location == "Room B"

    assert (
        updated.description
        == "Updated description"
    )

    assert len(client.update_calls) == 1


# =========================================================
# 7. TIME CHANGE WITH CONFLICT
# =========================================================

def test_time_change_conflict_is_blocked():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    conflicting_event = make_event(
        "event-2",
        "Meeting",
        dt(14),
        dt(15),
    )

    service, client = make_service(
        [
            event,
            conflicting_event,
        ]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_start=dt(14),
        new_end=dt(15),
    )

    result = service.update(
        request,
        [
            event,
            conflicting_event,
        ],
    )

    assert (
        result.status
        == "conflict_blocked"
    )

    assert result.event is None

    assert len(result.conflicts) == 1

    assert (
        result.conflicts[0].event_id
        == "event-2"
    )

    # IMPORTANT:
    # Google/fake connector must never receive
    # the update when conflict exists.

    assert len(client.update_calls) == 0


# =========================================================
# 8. AMBIGUOUS NATURAL-LANGUAGE MATCH
# =========================================================

def test_ambiguous_query_is_blocked():

    event_1 = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    event_2 = make_event(
        "event-2",
        "DSA",
        dt(14),
        dt(15),
    )

    service, client = make_service(
        [
            event_1,
            event_2,
        ]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        query="DSA",
        new_title="Advanced DSA",
    )

    result = service.update(
        request,
        [
            event_1,
            event_2,
        ],
    )

    assert result.status == "ambiguous"

    assert result.event is None

    assert len(result.candidates) == 2

    assert len(client.update_calls) == 0


# =========================================================
# 9. MISSING EVENT ID
# =========================================================

def test_missing_event_id():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    service, client = make_service(
        [event]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="does-not-exist",
        new_title="Updated",
    )

    result = service.update(
        request,
        [event],
    )

    assert result.status == "not_found"

    assert result.event is None

    assert len(client.update_calls) == 0


# =========================================================
# 10. MISSING QUERY RESULT
# =========================================================

def test_missing_query_result():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    service, client = make_service(
        [event]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        query="Physics",
        new_title="Updated",
    )

    result = service.update(
        request,
        [event],
    )

    assert result.status == "not_found"

    assert result.event is None

    assert result.candidates == []

    assert len(client.update_calls) == 0


# =========================================================
# 11. CRITICAL SELF-CONFLICT REGRESSION
# =========================================================

def test_time_update_excludes_current_event_from_conflicts():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    service, client = make_service(
        [event]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_start=dt(10),
        new_end=dt(12),
    )

    result = service.update(
        request,
        [event],
    )

    assert result.status == "updated"

    assert result.event is not None

    assert result.event.start == dt(10)

    assert result.event.end == dt(12)

    assert len(result.conflicts) == 0

    assert len(client.update_calls) == 1


# =========================================================
# 12. TOUCHING BOUNDARY IS NOT A CONFLICT
# =========================================================

def test_touching_boundary_is_allowed():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    next_event = make_event(
        "event-2",
        "Meeting",
        dt(12),
        dt(13),
    )

    service, client = make_service(
        [
            event,
            next_event,
        ]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_start=dt(11),
        new_end=dt(12),
    )

    result = service.update(
        request,
        [
            event,
            next_event,
        ],
    )

    assert result.status == "updated"

    assert result.event is not None

    assert result.event.start == dt(11)

    assert result.event.end == dt(12)

    assert len(result.conflicts) == 0

    assert len(client.update_calls) == 1


# =========================================================
# 13. INVALID TIME RANGE
# =========================================================

def test_invalid_time_range():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    service, client = make_service(
        [event]
    )

    with pytest.raises(
        ValueError,
        match="new_end must be after new_start",
    ):

        CalendarUpdateRequest(
            operation=CalendarOperation.UPDATE,
            event_id="event-1",
            new_start=dt(15),
            new_end=dt(14),
        )

    # Validation must happen before any connector write.
    assert len(client.update_calls) == 0


# =========================================================
# 14. UPDATE VIA UNIQUE QUERY
# =========================================================

def test_update_via_unique_query():

    event = make_event(
        "event-1",
        "Nexus AI",
        dt(17),
        dt(18),
    )

    service, client = make_service(
        [event]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        query="Nexus AI",
        new_title="Nexus AI Project",
    )

    result = service.update(
        request,
        [event],
    )

    assert result.status == "updated"

    assert result.event is not None

    assert (
        result.event.title
        == "Nexus AI Project"
    )

    assert len(client.update_calls) == 1


# =========================================================
# 15. NO SILENT UPDATE ON CONNECTOR FAILURE
# =========================================================

def test_connector_failure_does_not_report_updated():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    class FailingClient:

        def __init__(self):
            self.update_calls = 0

        def update_event(self, event):

            self.update_calls += 1

            raise RuntimeError(
                "Simulated Google Calendar failure"
            )

    client = FailingClient()

    service = CalendarUpdateService(
        client=client,
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_title="Updated DSA",
    )

    with pytest.raises(RuntimeError):

        service.update(
            request,
            [event],
        )

    assert client.update_calls == 1