from datetime import datetime
from zoneinfo import ZoneInfo

from datetime_utils import DateTimeRange
from free_slot_service import FreeSlotService
from models import EventSummary
from next_slot import NextSlotService


IST = ZoneInfo("Asia/Kolkata")


def dt(
    day: int,
    hour: int,
    minute: int = 0,
) -> datetime:
    return datetime(
        2026,
        8,
        day,
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


def create_service() -> NextSlotService:
    return NextSlotService(
        free_slot_service=FreeSlotService(),
    )


def test_fully_booked_today_then_free_tomorrow():

    events = [
        make_event(
            "today-busy",
            dt(12, 9),
            dt(12, 23, 59),
        ),
    ]

    service = create_service()

    result = service.find_next_free_slot(
        events=events,
        earliest_start=dt(12, 8),
        duration_minutes=120,
        horizon_days=2,
    )

    assert result is not None

    assert result.start == dt(13, 0)
    assert result.end.hour == 23
    assert result.end.minute == 59
    assert result.end.second == 59
    assert result.end.microsecond == 999999
    assert result.duration_minutes >= 120


def test_free_later_today_is_selected_before_tomorrow():

    events = [
        make_event(
            "busy",
            dt(12, 9),
            dt(12, 14),
        ),
    ]

    service = create_service()

    result = service.find_next_free_slot(
        events=events,
        earliest_start=dt(12, 10),
        duration_minutes=120,
        horizon_days=2,
    )

    assert result is not None

    assert result.start == dt(12, 14)


def test_exact_duration_slot_is_returned_unchanged():

    events = [
        make_event(
            "busy-a",
            dt(12, 8),
            dt(12, 10),
        ),
        make_event(
            "busy-b",
            dt(12, 11),
            dt(12, 18),
        ),
    ]

    service = create_service()

    result = service.find_next_free_slot(
        events=events,
        earliest_start=dt(12, 8),
        duration_minutes=60,
        horizon_days=1,
    )

    assert result is not None

    assert result.start == dt(12, 10)
    assert result.end == dt(12, 11)
    assert result.duration_minutes == 60


def test_longer_slot_is_returned_in_full():

    events = [
        make_event(
            "busy-a",
            dt(12, 8),
            dt(12, 10),
        ),
        make_event(
            "busy-b",
            dt(12, 15),
            dt(12, 18),
        ),
    ]

    service = create_service()

    result = service.find_next_free_slot(
        events=events,
        earliest_start=dt(12, 8),
        duration_minutes=60,
        horizon_days=1,
    )

    assert result is not None

    assert result.start == dt(12, 10)
    assert result.end == dt(12, 15)
    assert result.duration_minutes == 300


def test_late_night_request_rolls_to_next_day():

    events = [
        make_event(
            "late-busy",
            dt(12, 23, 50),
            dt(12, 23, 59),
        ),
    ]

    service = create_service()

    result = service.find_next_free_slot(
        events=events,
        earliest_start=dt(12, 23, 50),
        duration_minutes=60,
        horizon_days=2,
    )

    assert result is not None

    assert result.start.date() == dt(13, 0).date()

    assert result.start == dt(13, 0)


def test_returns_none_when_no_slot_exists_within_horizon():

    events = [
        make_event(
            "busy-1",
            dt(12, 0),
            dt(12, 23, 59),
        ),
        make_event(
            "busy-2",
            dt(13, 0),
            dt(13, 23, 59),
        ),
        make_event(
            "busy-3",
            dt(14, 0),
            dt(14, 23, 59),
        ),
    ]

    service = create_service()

    result = service.find_next_free_slot(
        events=events,
        earliest_start=dt(12, 0),
        duration_minutes=60,
        horizon_days=3,
    )

    assert result is None


def test_earliest_valid_slot_wins():

    events = [
        make_event(
            "busy-a",
            dt(12, 10),
            dt(12, 11),
        ),
        make_event(
            "busy-b",
            dt(12, 13),
            dt(12, 14),
        ),
    ]

    service = create_service()

    result = service.find_next_free_slot(
        events=events,
        earliest_start=dt(12, 8),
        duration_minutes=120,
        horizon_days=1,
    )

    assert result is not None

    # 08:00 -> 10:00 is the first valid 2-hour slot.
    assert result.start == dt(12, 8)
    assert result.end == dt(12, 10)
    assert result.duration_minutes == 120