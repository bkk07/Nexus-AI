from datetime import datetime
from zoneinfo import ZoneInfo

from models import EventSummary
from next_slot import NextSlotService


IST = ZoneInfo("Asia/Kolkata")


def dt(day: int, hour: int, minute: int = 0) -> datetime:
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


def test_free_right_now_returns_immediately():

    events = []

    service = NextSlotService()

    result = service.find_next_free_slot(
        events=events,
        earliest_start=dt(12, 10),
        duration_minutes=60,
    )

    assert result is not None

    assert result.start == dt(12, 10)
    assert result.end > result.start
    assert result.duration_minutes >= 60


def test_later_today_is_returned_not_passed_slot():

    events = [
        make_event(
            "busy-1",
            dt(12, 9),
            dt(12, 11),
        ),
    ]

    service = NextSlotService()

    result = service.find_next_free_slot(
        events=events,
        earliest_start=dt(12, 10),
        duration_minutes=60,
    )

    assert result is not None

    assert result.start >= dt(12, 11)


def test_advances_to_tomorrow():

    events = [
        make_event(
            "busy-1",
            dt(12, 9),
            dt(12, 23),
        ),
    ]

    service = NextSlotService()

    result = service.find_next_free_slot(
        events=events,
        earliest_start=dt(12, 10),
        duration_minutes=120,
    )

    assert result is not None

    assert result.start.date() > dt(12, 10).date()


def test_returns_none_when_horizon_exhausted():

    events = []

    service = NextSlotService()

    result = service.find_next_free_slot(
        events=events,
        earliest_start=dt(12, 10),
        duration_minutes=25 * 60,
        horizon_days=3,
    )

    assert result is None


def test_exact_duration_match_is_returned():

    events = [
        make_event(
            "busy-1",
            dt(12, 8),
            dt(12, 10),
        ),
        make_event(
            "busy-2",
            dt(12, 11),
            dt(12, 18),
        ),
    ]

    service = NextSlotService()

    result = service.find_next_free_slot(
        events=events,
        earliest_start=dt(12, 8),
        duration_minutes=60,
    )

    assert result is not None

    assert result.start == dt(12, 10)
    assert result.end == dt(12, 11)
    assert result.duration_minutes == 60


def test_longer_slot_is_not_truncated():

    events = [
        make_event(
            "busy-1",
            dt(12, 8),
            dt(12, 10),
        ),
        make_event(
            "busy-2",
            dt(12, 15),
            dt(12, 18),
        ),
    ]

    service = NextSlotService()

    result = service.find_next_free_slot(
        events=events,
        earliest_start=dt(12, 8),
        duration_minutes=60,
    )

    assert result is not None

    assert result.start == dt(12, 10)
    assert result.end == dt(12, 15)

    assert result.duration_minutes == 300