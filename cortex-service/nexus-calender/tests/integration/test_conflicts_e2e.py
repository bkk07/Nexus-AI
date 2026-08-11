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


def test_clean_calendar_has_no_conflicts():

    events = [
        make_event(
            "busy-a",
            dt(9),
            dt(10),
        ),
        make_event(
            "busy-b",
            dt(14),
            dt(15),
        ),
    ]

    proposed = make_range(
        dt(11),
        dt(13),
    )

    result = find_conflicts(
        proposed,
        events,
    )

    assert result == []


def test_overlapping_event_is_detected():

    events = [
        make_event(
            "busy-a",
            dt(9),
            dt(10),
        ),
        make_event(
            "busy-b",
            dt(10, 30),
            dt(12),
        ),
        make_event(
            "busy-c",
            dt(14),
            dt(15),
        ),
    ]

    proposed = make_range(
        dt(11),
        dt(13),
    )

    result = find_conflicts(
        proposed,
        events,
    )

    assert [
        event.event_id
        for event in result
    ] == [
        "busy-b",
    ]


def test_multiple_overlapping_events_are_all_returned():

    events = [
        make_event(
            "busy-a",
            dt(9),
            dt(11),
        ),
        make_event(
            "busy-b",
            dt(10),
            dt(12),
        ),
        make_event(
            "busy-c",
            dt(11, 30),
            dt(13),
        ),
        make_event(
            "busy-d",
            dt(15),
            dt(16),
        ),
    ]

    proposed = make_range(
        dt(10, 30),
        dt(12, 30),
    )

    result = find_conflicts(
        proposed,
        events,
    )

    assert [
        event.event_id
        for event in result
    ] == [
        "busy-a",
        "busy-b",
        "busy-c",
    ]


def test_adjacent_events_are_not_conflicts():

    events = [
        make_event(
            "busy-before",
            dt(9),
            dt(10),
        ),
        make_event(
            "busy-after",
            dt(12),
            dt(13),
        ),
    ]

    proposed = make_range(
        dt(10),
        dt(12),
    )

    result = find_conflicts(
        proposed,
        events,
    )

    assert result == []


def test_event_ending_at_start_is_not_conflict():

    events = [
        make_event(
            "busy-before",
            dt(9),
            dt(11),
        ),
    ]

    proposed = make_range(
        dt(11),
        dt(13),
    )

    result = find_conflicts(
        proposed,
        events,
    )

    assert result == []


def test_event_starting_at_end_is_not_conflict():

    events = [
        make_event(
            "busy-after",
            dt(13),
            dt(15),
        ),
    ]

    proposed = make_range(
        dt(11),
        dt(13),
    )

    result = find_conflicts(
        proposed,
        events,
    )

    assert result == []


def test_fully_contained_event_is_conflict():

    events = [
        make_event(
            "busy-a",
            dt(10),
            dt(11),
        ),
    ]

    proposed = make_range(
        dt(9),
        dt(12),
    )

    result = find_conflicts(
        proposed,
        events,
    )

    assert [
        event.event_id
        for event in result
    ] == [
        "busy-a",
    ]


def test_proposed_range_inside_event_is_conflict():

    events = [
        make_event(
            "busy-a",
            dt(9),
            dt(15),
        ),
    ]

    proposed = make_range(
        dt(11),
        dt(12),
    )

    result = find_conflicts(
        proposed,
        events,
    )

    assert [
        event.event_id
        for event in result
    ] == [
        "busy-a",
    ]


def test_overlapping_events_are_not_merged():

    events = [
        make_event(
            "busy-a",
            dt(9),
            dt(12),
        ),
        make_event(
            "busy-b",
            dt(10),
            dt(13),
        ),
        make_event(
            "busy-c",
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
        "busy-a",
        "busy-b",
        "busy-c",
    ]

    # Important Phase 11 guarantee:
    # conflicts remain individual EventSummary objects.
    assert result[0].start == dt(9)
    assert result[0].end == dt(12)

    assert result[1].start == dt(10)
    assert result[1].end == dt(13)

    assert result[2].start == dt(11)
    assert result[2].end == dt(14)


def test_realistic_schedule_returns_exact_conflicts():

    events = [
        make_event(
            "busy-a",
            dt(9),
            dt(10),
        ),
        make_event(
            "busy-b",
            dt(9, 30),
            dt(11),
        ),
        make_event(
            "busy-c",
            dt(11),
            dt(12),
        ),
        make_event(
            "busy-d",
            dt(14),
            dt(15),
        ),
        make_event(
            "busy-e",
            dt(14, 30),
            dt(16),
        ),
        make_event(
            "busy-f",
            dt(17),
            dt(18),
        ),
        make_event(
            "busy-g",
            dt(20),
            dt(22),
        ),
    ]

    # Proposed 10:30 -> 15:30 overlaps:
    #
    # busy-b  09:30 -> 11:00
    # busy-c  11:00 -> 12:00
    # busy-d  14:00 -> 15:00
    # busy-e  14:30 -> 16:00
    #
    # busy-a ends at 10:00 -> no conflict.
    proposed = make_range(
        dt(10, 30),
        dt(15, 30),
    )

    result = find_conflicts(
        proposed,
        events,
    )

    assert [
        event.event_id
        for event in result
    ] == [
        "busy-b",
        "busy-c",
        "busy-d",
        "busy-e",
    ]