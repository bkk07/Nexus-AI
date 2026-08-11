from datetime import datetime
from zoneinfo import ZoneInfo

from conflicts import find_conflicts
from datetime_utils import DateTimeRange
from models import EventSummary


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
    start: datetime,
    end: datetime,
) -> EventSummary:

    return EventSummary(
        event_id=event_id,
        title=f"Event {event_id}",
        start=start,
        end=end,
    )


def make_range(
    start: datetime,
    end: datetime,
) -> DateTimeRange:

    return DateTimeRange(
        start=start,
        end=end,
    )


def test_no_conflict():

    events = [
        make_event(
            "event-1",
            dt(9),
            dt(10),
        )
    ]

    proposed = make_range(
        dt(11),
        dt(12),
    )

    result = find_conflicts(
        proposed,
        events,
    )

    assert result == []


def test_one_conflict():

    event = make_event(
        "event-1",
        dt(10),
        dt(11),
    )

    proposed = make_range(
        dt(10, 30),
        dt(11, 30),
    )

    result = find_conflicts(
        proposed,
        [event],
    )

    assert len(result) == 1
    assert result[0].event_id == "event-1"


def test_multiple_conflicts():

    events = [
        make_event(
            "event-1",
            dt(9),
            dt(11),
        ),
        make_event(
            "event-2",
            dt(10, 30),
            dt(12),
        ),
        make_event(
            "event-3",
            dt(13),
            dt(14),
        ),
    ]

    proposed = make_range(
        dt(10),
        dt(11, 30),
    )

    result = find_conflicts(
        proposed,
        events,
    )

    assert [
        event.event_id
        for event in result
    ] == [
        "event-1",
        "event-2",
    ]


def test_boundary_touching_is_not_conflict():

    event = make_event(
        "event-1",
        dt(10),
        dt(11),
    )

    proposed = make_range(
        dt(11),
        dt(12),
    )

    result = find_conflicts(
        proposed,
        [event],
    )

    assert result == []


def test_fully_containing_event_is_conflict():

    event = make_event(
        "event-1",
        dt(9),
        dt(14),
    )

    proposed = make_range(
        dt(10),
        dt(11),
    )

    result = find_conflicts(
        proposed,
        [event],
    )

    assert len(result) == 1
    assert result[0].event_id == "event-1"


def test_proposed_range_fully_contains_event():

    event = make_event(
        "event-1",
        dt(10),
        dt(11),
    )

    proposed = make_range(
        dt(9),
        dt(12),
    )

    result = find_conflicts(
        proposed,
        [event],
    )

    assert len(result) == 1
    assert result[0].event_id == "event-1"


def test_multiple_overlapping_events_remain_individual():

    events = [
        make_event(
            "event-1",
            dt(9),
            dt(12),
        ),
        make_event(
            "event-2",
            dt(10),
            dt(13),
        ),
        make_event(
            "event-3",
            dt(11),
            dt(14),
        ),
    ]

    proposed = make_range(
        dt(10, 30),
        dt(11, 30),
    )

    result = find_conflicts(
        proposed,
        events,
    )

    assert len(result) == 3

    assert [
        event.event_id
        for event in result
    ] == [
        "event-1",
        "event-2",
        "event-3",
    ]