from datetime import datetime
from zoneinfo import ZoneInfo

from datetime_utils import DateTimeRange
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
        title=f"Event {event_id}",
        start=start,
        end=end,
    )


def test_service_finds_free_slots_from_events():

    service = FreeSlotService()

    events = [
        make_event(
            "event-1",
            dt(10),
            dt(11),
        ),
        make_event(
            "event-2",
            dt(13),
            dt(14),
        ),
    ]

    window = DateTimeRange(
        start=dt(9),
        end=dt(17),
    )

    result = service.find_free_slots(
        events=events,
        window=window,
    )

    assert [
        (
            slot.start,
            slot.end,
        )
        for slot in result
    ] == [
        (dt(9), dt(10)),
        (dt(11), dt(13)),
        (dt(14), dt(17)),
    ]


def test_service_merges_overlapping_events():

    service = FreeSlotService()

    events = [
        make_event(
            "event-1",
            dt(9),
            dt(11),
        ),
        make_event(
            "event-2",
            dt(10),
            dt(12),
        ),
    ]

    window = DateTimeRange(
        start=dt(9),
        end=dt(14),
    )

    result = service.find_free_slots(
        events=events,
        window=window,
    )

    assert len(result) == 1

    assert result[0].start == dt(12)
    assert result[0].end == dt(14)


def test_service_respects_minimum_duration():

    service = FreeSlotService()

    events = [
        make_event(
            "event-1",
            dt(10),
            dt(10, 30),
        ),
        make_event(
            "event-2",
            dt(11),
            dt(14),
        ),
    ]

    window = DateTimeRange(
        start=dt(9),
        end=dt(15),
    )

    result = service.find_free_slots(
        events=events,
        window=window,
        minimum_duration_minutes=60,
    )

    assert [
        slot.duration_minutes
        for slot in result
    ] == [
        60,
        60,
    ]