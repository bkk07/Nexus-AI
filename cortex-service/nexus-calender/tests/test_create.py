from datetime import datetime
from zoneinfo import ZoneInfo

from create import CalendarCreateService
from models import (
    CalendarCreateRequest,
    EventSummary,
)


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


def make_request(
    title: str,
    start: datetime,
    end: datetime,
) -> CalendarCreateRequest:

    return CalendarCreateRequest(
        title=title,
        start=start,
        end=end,
    )


class FakeCalendarClient:
    """
    Fake client used for unit tests.

    It records every create_event() call so we can prove
    that blocked operations never reach the connector.
    """

    def __init__(self) -> None:

        self.create_calls: list[EventSummary] = []

    def search(self, query):
        return []

    def create_event(
        self,
        event: EventSummary,
    ) -> EventSummary:

        self.create_calls.append(event)

        return EventSummary(
            event_id="created-event",
            title=event.title,
            start=event.start,
            end=event.end,
            location=event.location,
            description=event.description,
        )


def test_normal_creation_is_allowed():

    client = FakeCalendarClient()

    service = CalendarCreateService(
        client=client,
    )

    request = make_request(
        "DSA Practice",
        dt(10),
        dt(11),
    )

    result = service.create(
        request,
        existing_events=[],
    )

    assert result.status == "created"

    assert result.event is not None

    assert result.event.title == "DSA Practice"

    assert result.event.start == dt(10)

    assert result.event.end == dt(11)

    assert len(client.create_calls) == 1


def test_exact_duplicate_is_blocked():

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

    request = make_request(
        "DSA Practice",
        dt(10),
        dt(11),
    )

    result = service.create(
        request,
        existing_events=[existing],
    )

    assert result.status == "duplicate_blocked"

    assert result.existing_duplicate is not None

    assert (
        result.existing_duplicate.event_id
        == "event-1"
    )

    assert result.conflicts == []

    # Critical safety guarantee:
    # duplicate must never reach create_event().
    assert client.create_calls == []


def test_duplicate_title_with_different_time_is_allowed():

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

    request = make_request(
        "DSA Practice",
        dt(12),
        dt(13),
    )

    result = service.create(
        request,
        existing_events=[existing],
    )

    assert result.status == "created"

    assert len(client.create_calls) == 1


def test_different_title_same_time_is_conflict():

    client = FakeCalendarClient()

    existing = make_event(
        "event-1",
        "Meeting",
        dt(10),
        dt(11),
    )

    service = CalendarCreateService(
        client=client,
    )

    request = make_request(
        "DSA Practice",
        dt(10),
        dt(11),
    )

    result = service.create(
        request,
        existing_events=[existing],
    )

    assert result.status == "conflict_blocked"

    assert len(result.conflicts) == 1

    assert (
        result.conflicts[0].event_id
        == "event-1"
    )

    # Conflict must never reach Google.
    assert client.create_calls == []


def test_overlapping_event_is_conflict():

    client = FakeCalendarClient()

    existing = make_event(
        "event-1",
        "Meeting",
        dt(10),
        dt(12),
    )

    service = CalendarCreateService(
        client=client,
    )

    request = make_request(
        "DSA Practice",
        dt(11),
        dt(13),
    )

    result = service.create(
        request,
        existing_events=[existing],
    )

    assert result.status == "conflict_blocked"

    assert len(result.conflicts) == 1

    assert client.create_calls == []


def test_multiple_conflicts_are_returned():

    client = FakeCalendarClient()

    events = [
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

    request = make_request(
        "DSA Practice",
        dt(10, 30),
        dt(11, 30),
    )

    result = service.create(
        request,
        existing_events=events,
    )

    assert result.status == "conflict_blocked"

    assert [
        event.event_id
        for event in result.conflicts
    ] == [
        "event-1",
        "event-2",
    ]

    assert client.create_calls == []


def test_touching_event_is_allowed():

    client = FakeCalendarClient()

    existing = make_event(
        "event-1",
        "Meeting",
        dt(9),
        dt(10),
    )

    service = CalendarCreateService(
        client=client,
    )

    request = make_request(
        "DSA Practice",
        dt(10),
        dt(11),
    )

    result = service.create(
        request,
        existing_events=[existing],
    )

    assert result.status == "created"

    assert result.conflicts == []

    assert len(client.create_calls) == 1


def test_event_after_requested_range_is_allowed():

    client = FakeCalendarClient()

    existing = make_event(
        "event-1",
        "Meeting",
        dt(12),
        dt(13),
    )

    service = CalendarCreateService(
        client=client,
    )

    request = make_request(
        "DSA Practice",
        dt(10),
        dt(11),
    )

    result = service.create(
        request,
        existing_events=[existing],
    )

    assert result.status == "created"

    assert len(client.create_calls) == 1


def test_case_and_whitespace_differences_still_detect_duplicate():

    client = FakeCalendarClient()

    existing = make_event(
        "event-1",
        "  DSA   Practice  ",
        dt(10),
        dt(11),
    )

    service = CalendarCreateService(
        client=client,
    )

    request = make_request(
        "dsa practice",
        dt(10),
        dt(11),
    )

    result = service.create(
        request,
        existing_events=[existing],
    )

    assert result.status == "duplicate_blocked"

    assert client.create_calls == []


def test_duplicate_check_happens_before_conflict_check():

    client = FakeCalendarClient()

    duplicate = make_event(
        "event-duplicate",
        "DSA Practice",
        dt(10),
        dt(11),
    )

    overlapping = make_event(
        "event-overlap",
        "Another Meeting",
        dt(10, 30),
        dt(11, 30),
    )

    service = CalendarCreateService(
        client=client,
    )

    request = make_request(
        "DSA Practice",
        dt(10),
        dt(11),
    )

    result = service.create(
        request,
        existing_events=[
            duplicate,
            overlapping,
        ],
    )

    # Duplicate takes priority.
    assert result.status == "duplicate_blocked"

    assert (
        result.existing_duplicate.event_id
        == "event-duplicate"
    )

    assert result.conflicts == []

    assert client.create_calls == []


def test_creation_preserves_location_and_description():

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

    assert len(client.create_calls) == 1


def test_negative_duplicate_tolerance_is_rejected():

    client = FakeCalendarClient()

    try:

        CalendarCreateService(
            client=client,
            duplicate_tolerance_minutes=-1,
        )

        assert False

    except ValueError as exc:

        assert (
            str(exc)
            == "duplicate_tolerance_minutes "
               "cannot be negative."
        )