from datetime import datetime

import pytest
from models import EventSummary
from busy_intervals import (
    BusyInterval,
    merge_busy_intervals,
)


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(
        2026,
        8,
        12,
        hour,
        minute,
    )


def test_overlapping_intervals_are_merged():

    intervals = [
        BusyInterval(
            start=dt(9),
            end=dt(10),
            source_event_ids=["event-1"],
        ),
        BusyInterval(
            start=dt(9, 30),
            end=dt(11),
            source_event_ids=["event-2"],
        ),
    ]

    result = merge_busy_intervals(intervals)

    assert len(result) == 1

    assert result[0].start == dt(9)
    assert result[0].end == dt(11)

    assert result[0].source_event_ids == [
        "event-1",
        "event-2",
    ]


def test_touching_intervals_are_merged():

    intervals = [
        BusyInterval(
            start=dt(10),
            end=dt(11),
            source_event_ids=["event-1"],
        ),
        BusyInterval(
            start=dt(11),
            end=dt(12),
            source_event_ids=["event-2"],
        ),
    ]

    result = merge_busy_intervals(intervals)

    assert len(result) == 1

    assert result[0].start == dt(10)
    assert result[0].end == dt(12)

    assert set(result[0].source_event_ids) == {
        "event-1",
        "event-2",
    }


def test_non_overlapping_intervals_remain_separate():

    intervals = [
        BusyInterval(
            start=dt(9),
            end=dt(10),
            source_event_ids=["event-1"],
        ),
        BusyInterval(
            start=dt(11),
            end=dt(12),
            source_event_ids=["event-2"],
        ),
    ]

    result = merge_busy_intervals(intervals)

    assert len(result) == 2

    assert result[0].start == dt(9)
    assert result[0].end == dt(10)

    assert result[1].start == dt(11)
    assert result[1].end == dt(12)


def test_intervals_are_sorted_before_merging():

    intervals = [
        BusyInterval(
            start=dt(13),
            end=dt(14),
            source_event_ids=["event-3"],
        ),
        BusyInterval(
            start=dt(9),
            end=dt(10),
            source_event_ids=["event-1"],
        ),
        BusyInterval(
            start=dt(10),
            end=dt(12),
            source_event_ids=["event-2"],
        ),
    ]

    result = merge_busy_intervals(intervals)

    assert len(result) == 2

    assert result[0].start == dt(9)
    assert result[0].end == dt(12)

    assert result[1].start == dt(13)
    assert result[1].end == dt(14)

    assert set(result[0].source_event_ids) == {
        "event-1",
        "event-2",
    }


def test_multiple_overlapping_intervals():

    intervals = [
        BusyInterval(
            start=dt(9),
            end=dt(11),
            source_event_ids=["event-1"],
        ),
        BusyInterval(
            start=dt(10),
            end=dt(12),
            source_event_ids=["event-2"],
        ),
        BusyInterval(
            start=dt(11, 30),
            end=dt(13),
            source_event_ids=["event-3"],
        ),
    ]

    result = merge_busy_intervals(intervals)

    assert len(result) == 1

    assert result[0].start == dt(9)
    assert result[0].end == dt(13)

    assert set(result[0].source_event_ids) == {
        "event-1",
        "event-2",
        "event-3",
    }


def test_empty_input_returns_empty_list():

    result = merge_busy_intervals([])

    assert result == []


def test_invalid_zero_duration_interval_is_rejected():

    intervals = [
        BusyInterval(
            start=dt(10),
            end=dt(10),
            source_event_ids=["event-1"],
        )
    ]

    with pytest.raises(ValueError):
        merge_busy_intervals(intervals)


def test_invalid_negative_duration_interval_is_rejected():

    intervals = [
        BusyInterval(
            start=dt(11),
            end=dt(10),
            source_event_ids=["event-1"],
        )
    ]

    with pytest.raises(ValueError):
        merge_busy_intervals(intervals)


def test_duplicate_event_ids_are_not_duplicated():

    intervals = [
        BusyInterval(
            start=dt(9),
            end=dt(10),
            source_event_ids=["event-1"],
        ),
        BusyInterval(
            start=dt(9, 30),
            end=dt(11),
            source_event_ids=["event-1"],
        ),
    ]

    result = merge_busy_intervals(intervals)

    assert len(result) == 1

    assert result[0].source_event_ids == [
        "event-1"
    ]


def test_input_list_is_not_modified():

    intervals = [
        BusyInterval(
            start=dt(11),
            end=dt(12),
            source_event_ids=["event-2"],
        ),
        BusyInterval(
            start=dt(9),
            end=dt(10),
            source_event_ids=["event-1"],
        ),
    ]

    original_order = [
        interval.start
        for interval in intervals
    ]

    merge_busy_intervals(intervals)

    assert [
        interval.start
        for interval in intervals
    ] == original_order


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

def test_events_are_converted_to_busy_intervals():

    from busy_intervals import events_to_busy_intervals

    events = [
        make_event(
            "event-1",
            dt(9),
            dt(10),
        ),
        make_event(
            "event-2",
            dt(12),
            dt(13),
        ),
    ]

    result = events_to_busy_intervals(
        events
    )

    assert len(result) == 2

    assert result[0].start == dt(9)
    assert result[0].end == dt(10)
    assert result[0].source_event_ids == [
        "event-1"
    ]

    assert result[1].start == dt(12)
    assert result[1].end == dt(13)
    assert result[1].source_event_ids == [
        "event-2"
    ]


def test_overlapping_events_are_merged():

    from busy_intervals import events_to_busy_intervals

    events = [
        make_event(
            "event-1",
            dt(9),
            dt(10),
        ),
        make_event(
            "event-2",
            dt(9, 30),
            dt(11),
        ),
    ]

    result = events_to_busy_intervals(
        events
    )

    assert len(result) == 1

    assert result[0].start == dt(9)
    assert result[0].end == dt(11)

    assert set(
        result[0].source_event_ids
    ) == {
        "event-1",
        "event-2",
    }

def test_touching_events_are_merged():

    from busy_intervals import events_to_busy_intervals

    events = [
        make_event(
            "event-1",
            dt(9),
            dt(10),
        ),
        make_event(
            "event-2",
            dt(10),
            dt(11),
        ),
    ]

    result = events_to_busy_intervals(
        events
    )

    assert len(result) == 1

    assert result[0].start == dt(9)
    assert result[0].end == dt(11)

    assert set(
        result[0].source_event_ids
    ) == {
        "event-1",
        "event-2",
    }
def test_realistic_calendar_is_merged_correctly():

    from busy_intervals import events_to_busy_intervals

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
            dt(17, 30),
        ),
        make_event(
            "busy-g",
            dt(17),
            dt(18),
        ),
        make_event(
            "busy-h",
            dt(20),
            dt(22),
        ),
    ]

    result = events_to_busy_intervals(
        events
    )

    assert len(result) == 4

    assert (
        result[0].start,
        result[0].end,
    ) == (
        dt(9),
        dt(12),
    )

    assert (
        result[1].start,
        result[1].end,
    ) == (
        dt(14),
        dt(16),
    )

    assert (
        result[2].start,
        result[2].end,
    ) == (
        dt(17),
        dt(18),
    )

    assert (
        result[3].start,
        result[3].end,
    ) == (
        dt(20),
        dt(22),
    )
def test_invalid_event_is_rejected():

    from busy_intervals import events_to_busy_intervals

    events = [
        make_event(
            "invalid",
            dt(12),
            dt(11),
        )
    ]

    with pytest.raises(ValueError):

        events_to_busy_intervals(events)
