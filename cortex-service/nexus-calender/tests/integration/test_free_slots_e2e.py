from datetime import datetime
from zoneinfo import ZoneInfo

from datetime_utils import DateTimeRange
from engine.busy import BusyIntervalEngine
from free_slot_service import FreeSlotService
from models import EventSummary


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
    start: datetime,
    end: datetime,
) -> EventSummary:

    return EventSummary(
        event_id=event_id,
        title=f"Test Event {event_id}",
        start=start,
        end=end,
    )


def test_realistic_calendar_produces_expected_free_slots():

    events = [
        make_event("busy-a", dt(9), dt(10)),
        make_event("busy-b", dt(9, 30), dt(11)),
        make_event("busy-c", dt(12), dt(13)),
        make_event("busy-d", dt(14), dt(16)),
        make_event("busy-e", dt(17), dt(18)),
    ]

    window = DateTimeRange(
        start=dt(9),
        end=dt(20),
    )

    service = FreeSlotService()

    result = service.find_free_slots(
        events=events,
        window=window,
        minimum_duration_minutes=1,
    )

    assert [
        (
            slot.start,
            slot.end,
            slot.duration_minutes,
        )
        for slot in result
    ] == [
        (dt(11), dt(12), 60),
        (dt(13), dt(14), 60),
        (dt(16), dt(17), 60),
        (dt(18), dt(20), 120),
    ]


def test_minimum_30_minutes():

    events = [
        make_event("busy-a", dt(9), dt(10)),
        make_event("busy-b", dt(10, 30), dt(12)),
        make_event("busy-c", dt(13), dt(15)),
    ]

    window = DateTimeRange(
        start=dt(9),
        end=dt(16),
    )

    service = FreeSlotService()

    result = service.find_free_slots(
        events=events,
        window=window,
        minimum_duration_minutes=30,
    )

    assert [
        slot.duration_minutes
        for slot in result
    ] == [
        30,
        60,
        60,
    ]


def test_minimum_60_minutes():

    events = [
        make_event("busy-a", dt(9), dt(10)),
        make_event("busy-b", dt(10, 30), dt(12)),
        make_event("busy-c", dt(13), dt(15)),
    ]

    window = DateTimeRange(
        start=dt(9),
        end=dt(16),
    )

    service = FreeSlotService()

    result = service.find_free_slots(
        events=events,
        window=window,
        minimum_duration_minutes=60,
    )

    assert [
        (
            slot.start,
            slot.end,
        )
        for slot in result
    ] == [
        (dt(12), dt(13)),
        (dt(15), dt(16)),
    ]


def test_minimum_90_minutes():

    events = [
        make_event("busy-a", dt(9), dt(10)),
        make_event("busy-b", dt(10, 30), dt(12)),
        make_event("busy-c", dt(13), dt(15)),
    ]

    window = DateTimeRange(
        start=dt(9),
        end=dt(17),
    )

    service = FreeSlotService()

    result = service.find_free_slots(
        events=events,
        window=window,
        minimum_duration_minutes=90,
    )

    assert [
        (
            slot.start,
            slot.end,
        )
        for slot in result
    ] == [
        (dt(15), dt(17)),
    ]


def test_minimum_120_minutes():

    events = [
        make_event("busy-a", dt(9), dt(10)),
        make_event("busy-b", dt(11), dt(12)),
        make_event("busy-c", dt(13), dt(14)),
    ]

    window = DateTimeRange(
        start=dt(9),
        end=dt(17),
    )

    service = FreeSlotService()

    result = service.find_free_slots(
        events=events,
        window=window,
        minimum_duration_minutes=120,
    )

    assert [
        (
            slot.start,
            slot.end,
        )
        for slot in result
    ] == [
        (dt(14), dt(17)),
    ]


def test_overlapping_events_are_merged_before_free_slot_calculation():

    events = [
        make_event("busy-a", dt(9), dt(11)),
        make_event("busy-b", dt(10), dt(12)),
        make_event("busy-c", dt(11, 30), dt(13)),
    ]

    window = DateTimeRange(
        start=dt(9),
        end=dt(17),
    )

    service = FreeSlotService()

    result = service.find_free_slots(
        events=events,
        window=window,
        minimum_duration_minutes=1,
    )

    assert [
        (
            slot.start,
            slot.end,
        )
        for slot in result
    ] == [
        (dt(13), dt(17)),
    ]


def test_back_to_back_events_create_no_artificial_free_slot():

    events = [
        make_event("busy-a", dt(9), dt(10)),
        make_event("busy-b", dt(10), dt(11)),
        make_event("busy-c", dt(11), dt(12)),
    ]

    window = DateTimeRange(
        start=dt(9),
        end=dt(13),
    )

    service = FreeSlotService()

    result = service.find_free_slots(
        events=events,
        window=window,
        minimum_duration_minutes=1,
    )

    assert len(result) == 1

    assert result[0].start == dt(12)
    assert result[0].end == dt(13)


def test_completely_busy_window_returns_no_slots():

    events = [
        make_event(
            "busy-a",
            dt(9),
            dt(17),
        ),
    ]

    window = DateTimeRange(
        start=dt(9),
        end=dt(17),
    )

    service = FreeSlotService()

    result = service.find_free_slots(
        events=events,
        window=window,
    )

    assert result == []


def test_completely_free_window_returns_one_slot():

    window = DateTimeRange(
        start=dt(9),
        end=dt(17),
    )

    service = FreeSlotService()

    result = service.find_free_slots(
        events=[],
        window=window,
        minimum_duration_minutes=60,
    )

    assert len(result) == 1

    assert result[0].start == dt(9)
    assert result[0].end == dt(17)
    assert result[0].duration_minutes == 480