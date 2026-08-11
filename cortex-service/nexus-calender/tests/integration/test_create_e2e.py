from datetime import datetime
from zoneinfo import ZoneInfo

from create import CalendarCreateService
from models import CalendarCreateRequest, EventSummary


IST = ZoneInfo("Asia/Kolkata")


def dt(
    hour: int,
    minute: int = 0,
) -> datetime:
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

    def __init__(self):
        self.created_events: list[EventSummary] = []

    def search(self, query):
        return []

    def create_event(
        self,
        event: EventSummary,
    ) -> EventSummary:

        created = EventSummary(
            event_id=f"created-{len(self.created_events) + 1}",
            title=event.title,
            start=event.start,
            end=event.end,
            location=event.location,
            description=event.description,
        )

        self.created_events.append(created)

        return created


def test_create_clean_slot():

    client = FakeCalendarClient()

    service = CalendarCreateService(
        client=client,
    )

    request = CalendarCreateRequest(
        title="DSA Practice",
        start=dt(10),
        end=dt(11),
    )

    result = service.create(
        request,
        existing_events=[],
    )

    assert result.status == "created"

    assert result.event is not None

    assert result.event.event_id == "created-1"

    assert result.event.title == "DSA Practice"

    assert len(client.created_events) == 1


def test_duplicate_is_blocked_without_write():

    client = FakeCalendarClient()

    existing = make_event(
        "existing-1",
        "DSA Practice",
        dt(10),
        dt(11),
    )

    service = CalendarCreateService(
        client=client,
    )

    request = CalendarCreateRequest(
        title="DSA Practice",
        start=dt(10),
        end=dt(11),
    )

    result = service.create(
        request,
        existing_events=[existing],
    )

    assert result.status == "duplicate_blocked"

    assert result.existing_duplicate is not None

    assert (
        result.existing_duplicate.event_id
        == "existing-1"
    )

    assert client.created_events == []


def test_different_title_same_time_is_conflict():

    client = FakeCalendarClient()

    existing = make_event(
        "meeting-1",
        "Faculty Meeting",
        dt(10),
        dt(11),
    )

    service = CalendarCreateService(
        client=client,
    )

    request = CalendarCreateRequest(
        title="DSA Practice",
        start=dt(10),
        end=dt(11),
    )

    result = service.create(
        request,
        existing_events=[existing],
    )

    assert result.status == "conflict_blocked"

    assert len(result.conflicts) == 1

    assert (
        result.conflicts[0].event_id
        == "meeting-1"
    )

    assert client.created_events == []


def test_overlapping_event_is_conflict():

    client = FakeCalendarClient()

    existing = make_event(
        "meeting-1",
        "Faculty Meeting",
        dt(10),
        dt(12),
    )

    service = CalendarCreateService(
        client=client,
    )

    request = CalendarCreateRequest(
        title="Project Work",
        start=dt(11),
        end=dt(13),
    )

    result = service.create(
        request,
        existing_events=[existing],
    )

    assert result.status == "conflict_blocked"

    assert [
        event.event_id
        for event in result.conflicts
    ] == [
        "meeting-1",
    ]

    assert client.created_events == []


def test_touching_events_are_allowed():

    client = FakeCalendarClient()

    existing = make_event(
        "meeting-1",
        "Faculty Meeting",
        dt(9),
        dt(10),
    )

    service = CalendarCreateService(
        client=client,
    )

    request = CalendarCreateRequest(
        title="Project Work",
        start=dt(10),
        end=dt(11),
    )

    result = service.create(
        request,
        existing_events=[existing],
    )

    assert result.status == "created"

    assert result.conflicts == []

    assert len(client.created_events) == 1


def test_same_title_different_time_is_allowed():

    client = FakeCalendarClient()

    existing = make_event(
        "event-1",
        "DSA Practice",
        dt(10),
        dt(11),
    )

    service = CalendarCreateService(
        client=client,
    )

    request = CalendarCreateRequest(
        title="DSA Practice",
        start=dt(12),
        end=dt(13),
    )

    result = service.create(
        request,
        existing_events=[existing],
    )

    assert result.status == "created"

    assert len(client.created_events) == 1


def test_multiple_conflicts_block_creation():

    client = FakeCalendarClient()

    existing_events = [
        make_event(
            "event-1",
            "Meeting A",
            dt(9),
            dt(11),
        ),
        make_event(
            "event-2",
            "Meeting B",
            dt(10),
            dt(12),
        ),
        make_event(
            "event-3",
            "Meeting C",
            dt(14),
            dt(15),
        ),
    ]

    service = CalendarCreateService(
        client=client,
    )

    request = CalendarCreateRequest(
        title="Project Work",
        start=dt(10, 30),
        end=dt(11, 30),
    )

    result = service.create(
        request,
        existing_events=existing_events,
    )

    assert result.status == "conflict_blocked"

    assert [
        event.event_id
        for event in result.conflicts
    ] == [
        "event-1",
        "event-2",
    ]

    assert client.created_events == []


def test_duplicate_has_priority_over_conflict():

    client = FakeCalendarClient()

    duplicate = make_event(
        "duplicate-1",
        "Project Work",
        dt(10),
        dt(11),
    )

    overlapping = make_event(
        "conflict-1",
        "Other Meeting",
        dt(10, 30),
        dt(11, 30),
    )

    service = CalendarCreateService(
        client=client,
    )

    request = CalendarCreateRequest(
        title="Project Work",
        start=dt(10),
        end=dt(11),
    )

    result = service.create(
        request,
        existing_events=[
            duplicate,
            overlapping,
        ],
    )

    assert result.status == "duplicate_blocked"

    assert (
        result.existing_duplicate.event_id
        == "duplicate-1"
    )

    assert result.conflicts == []

    assert client.created_events == []


def test_creation_preserves_event_metadata():

    client = FakeCalendarClient()

    service = CalendarCreateService(
        client=client,
    )

    request = CalendarCreateRequest(
        title="Project Work",
        start=dt(15),
        end=dt(16),
        location="Library",
        description="Backend development",
    )

    result = service.create(
        request,
        existing_events=[],
    )

    assert result.status == "created"

    assert result.event is not None

    assert result.event.location == "Library"

    assert (
        result.event.description
        == "Backend development"
    )

    assert len(client.created_events) == 1