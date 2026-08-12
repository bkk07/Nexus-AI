from datetime import datetime
from zoneinfo import ZoneInfo

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


class FakeCalendarClient:

    def __init__(
        self,
        events: list[EventSummary],
    ):
        self.events = {
            event.event_id: event
            for event in events
        }

        self.update_calls: list[EventSummary] = []

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


def create_service(
    events: list[EventSummary],
):
    client = FakeCalendarClient(events)

    service = CalendarUpdateService(
        client=client,
    )

    return service, client


# =========================================================
# 1. TITLE UPDATE
# =========================================================

def test_title_update():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    service, client = create_service(
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
# 2. LOCATION UPDATE
# =========================================================

def test_location_update():

    event = make_event(
        "event-1",
        "Meeting",
        dt(10),
        dt(11),
        location="Room A",
    )

    service, client = create_service(
        [event]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_location="Room B",
    )

    result = service.update(
        request,
        [event],
    )

    assert result.status == "updated"

    assert result.event is not None

    assert result.event.location == "Room B"

    assert len(client.update_calls) == 1


# =========================================================
# 3. DESCRIPTION UPDATE
# =========================================================

def test_description_update():

    event = make_event(
        "event-1",
        "Project",
        dt(10),
        dt(11),
        description="Old description",
    )

    service, client = create_service(
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

    assert len(client.update_calls) == 1


# =========================================================
# 4. MOVE TO FREE TIME
# =========================================================

def test_move_event_to_free_time():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    competing_event = make_event(
        "event-2",
        "Meeting",
        dt(14),
        dt(15),
    )

    service, client = create_service(
        [
            event,
            competing_event,
        ]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_start=dt(16),
        new_end=dt(17),
    )

    result = service.update(
        request,
        [
            event,
            competing_event,
        ],
    )

    assert result.status == "updated"

    assert result.event is not None

    assert result.event.start == dt(16)

    assert result.event.end == dt(17)

    assert len(result.conflicts) == 0

    assert len(client.update_calls) == 1


# =========================================================
# 5. MOVE INTO CONFLICT
# =========================================================

def test_move_event_into_conflicting_time():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    competing_event = make_event(
        "event-2",
        "Meeting",
        dt(14),
        dt(15),
    )

    service, client = create_service(
        [
            event,
            competing_event,
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
            competing_event,
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

    # No write must happen.
    assert len(client.update_calls) == 0

    # Original event remains unchanged.
    assert (
        client.events["event-1"].start
        == dt(10)
    )

    assert (
        client.events["event-1"].end
        == dt(11)
    )


# =========================================================
# 6. AMBIGUOUS NATURAL-LANGUAGE RESOLUTION
# =========================================================

def test_ambiguous_update_is_blocked():

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

    service, client = create_service(
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

    assert {
        event.event_id
        for event in result.candidates
    } == {
        "event-1",
        "event-2",
    }

    # Nothing must be written.
    assert len(client.update_calls) == 0


# =========================================================
# 7. MISSING EVENT
# =========================================================

def test_missing_event_is_not_found():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    service, client = create_service(
        [event]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="missing-event",
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
# 8. UNIQUE NATURAL-LANGUAGE RESOLUTION
# =========================================================

def test_unique_query_updates_correct_event():

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

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        query="Nexus AI",
        new_title="Nexus AI Project",
    )

    result = service.update(
        request,
        [
            target,
            other,
        ],
    )

    assert result.status == "updated"

    assert result.event is not None

    assert (
        result.event.event_id
        == "event-1"
    )

    assert (
        result.event.title
        == "Nexus AI Project"
    )

    assert len(client.update_calls) == 1


# =========================================================
# 9. MULTIPLE FIELDS ATOMICALLY
# =========================================================

def test_multiple_fields_update_atomically():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
        location="Room A",
        description="Old",
    )

    service, client = create_service(
        [event]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_title="Advanced DSA",
        new_start=dt(13),
        new_end=dt(15),
        new_location="Room B",
        new_description="Updated",
    )

    result = service.update(
        request,
        [event],
    )

    assert result.status == "updated"

    assert result.event is not None

    updated = result.event

    assert updated.event_id == "event-1"

    assert updated.title == "Advanced DSA"

    assert updated.start == dt(13)

    assert updated.end == dt(15)

    assert updated.location == "Room B"

    assert updated.description == "Updated"

    # Exactly one write.
    assert len(client.update_calls) == 1


# =========================================================
# 10. SELF-CONFLICT MUST BE EXCLUDED
# =========================================================

def test_update_does_not_conflict_with_itself():

    event = make_event(
        "event-1",
        "DSA",
        dt(10),
        dt(11),
    )

    service, client = create_service(
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

    assert result.conflicts == []

    assert len(client.update_calls) == 1


# =========================================================
# 11. TOUCHING BOUNDARY
# =========================================================

def test_update_touching_boundary_is_allowed():

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

    service, client = create_service(
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

    assert result.conflicts == []

    assert len(client.update_calls) == 1


# =========================================================
# 12. TIME UPDATE WITH MULTIPLE CONFLICTS
# =========================================================

def test_update_reports_all_conflicts():

    event = make_event(
        "event-1",
        "DSA",
        dt(9),
        dt(10),
    )

    conflict_1 = make_event(
        "event-2",
        "Meeting A",
        dt(14),
        dt(15),
    )

    conflict_2 = make_event(
        "event-3",
        "Meeting B",
        dt(14, 30),
        dt(16),
    )

    service, client = create_service(
        [
            event,
            conflict_1,
            conflict_2,
        ]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_start=dt(14),
        new_end=dt(15, 30),
    )

    result = service.update(
        request,
        [
            event,
            conflict_1,
            conflict_2,
        ],
    )

    assert (
        result.status
        == "conflict_blocked"
    )

    assert result.event is None

    assert {
        conflict.event_id
        for conflict in result.conflicts
    } == {
        "event-2",
        "event-3",
    }

    assert len(client.update_calls) == 0


# =========================================================
# 13. NON-TIME UPDATE DOES NOT CREATE CONFLICT
# =========================================================

def test_non_time_update_does_not_conflict():

    event = make_event(
        "event-1",
        "DSA",
        dt(14),
        dt(15),
    )

    another_event = make_event(
        "event-2",
        "Meeting",
        dt(14),
        dt(15),
    )

    service, client = create_service(
        [
            event,
            another_event,
        ]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_title="Advanced DSA",
    )

    result = service.update(
        request,
        [
            event,
            another_event,
        ],
    )

    assert result.status == "updated"

    assert result.event is not None

    assert result.event.title == "Advanced DSA"

    # Existing overlap does not matter because
    # the time itself did not change.
    assert result.conflicts == []

    assert len(client.update_calls) == 1


# =========================================================
# 14. UPDATE START ONLY
# =========================================================

def test_update_start_only():

    event = make_event(
        "event-1",
        "Project",
        dt(10),
        dt(12),
    )

    service, client = create_service(
        [event]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_start=dt(11),
    )

    result = service.update(
        request,
        [event],
    )

    assert result.status == "updated"

    assert result.event is not None

    assert result.event.start == dt(11)

    # Existing end is preserved.
    assert result.event.end == dt(12)

    assert len(client.update_calls) == 1


# =========================================================
# 15. UPDATE END ONLY
# =========================================================

def test_update_end_only():

    event = make_event(
        "event-1",
        "Project",
        dt(10),
        dt(12),
    )

    service, client = create_service(
        [event]
    )

    request = CalendarUpdateRequest(
        operation=CalendarOperation.UPDATE,
        event_id="event-1",
        new_end=dt(13),
    )

    result = service.update(
        request,
        [event],
    )

    assert result.status == "updated"

    assert result.event is not None

    assert result.event.start == dt(10)

    assert result.event.end == dt(13)

    assert len(client.update_calls) == 1