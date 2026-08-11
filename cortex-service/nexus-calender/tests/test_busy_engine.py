from datetime import datetime

from busy_intervals import BusyInterval
from engine.busy import BusyIntervalEngine
from models import EventSummary


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(
        2026,
        8,
        12,
        hour,
        minute,
    )


def event(
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


def test_empty_calendar_produces_no_busy_intervals():

    engine = BusyIntervalEngine()

    result = engine.build([])

    assert result == []


def test_single_event_becomes_one_busy_interval():

    engine = BusyIntervalEngine()

    events = [
        event(
            "event-1",
            dt(9),
            dt(10),
        )
    ]

    result = engine.build(events)

    assert len(result) == 1

    assert result[0].start == dt(9)
    assert result[0].end == dt(10)

    assert result[0].source_event_ids == [
        "event-1"
    ]


def test_overlapping_events_are_merged():

    engine = BusyIntervalEngine()

    events = [
        event(
            "event-1",
            dt(9),
            dt(10),
        ),
        event(
            "event-2",
            dt(9, 30),
            dt(11),
        ),
    ]

    result = engine.build(events)

    assert len(result) == 1

    assert result[0].start == dt(9)
    assert result[0].end == dt(11)

    assert set(
        result[0].source_event_ids
    ) == {
        "event-1",
        "event-2",
    }


def test_realistic_calendar():

    engine = BusyIntervalEngine()

    events = [
        event("A", dt(9), dt(10)),
        event("B", dt(9, 30), dt(11)),
        event("C", dt(11), dt(12)),
        event("D", dt(14), dt(15)),
        event("E", dt(14, 30), dt(16)),
        event("F", dt(17), dt(17, 30)),
        event("G", dt(17), dt(18)),
        event("H", dt(20), dt(22)),
    ]

    result = engine.build(events)

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