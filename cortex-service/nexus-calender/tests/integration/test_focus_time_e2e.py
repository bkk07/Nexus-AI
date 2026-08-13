from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from buffers import BufferConfig
from busy_intervals import BusyInterval
from datetime_utils import DateTimeRange
from engine.focus_time import find_focus_blocks


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


def busy(
    day: int,
    start_hour: int,
    end_hour: int,
    event_id: str,
) -> BusyInterval:
    return BusyInterval(
        start=dt(
            day,
            start_hour,
        ),
        end=dt(
            day,
            end_hour,
        ),
        source_event_ids=[event_id],
    )


def test_three_hour_uninterrupted_coding_time_tomorrow():
    """
    User request:

        "I need 3 hours uninterrupted coding time tomorrow."

    Simulated calendar:

        09:00 -> 10:00 busy
        13:00 -> 14:00 busy
        17:00 -> 18:00 busy

    Availability:

        08:00 -> 20:00

    Resulting free blocks:

        10:00 -> 13:00 = exactly 3 hours
        14:00 -> 17:00 = exactly 3 hours
        18:00 -> 20:00 = 2 hours

    Therefore two genuine 3-hour focus blocks should be
    returned.
    """

    tomorrow = 13

    window = DateTimeRange(
        start=dt(
            tomorrow,
            8,
        ),
        end=dt(
            tomorrow,
            20,
        ),
    )

    calendar_busy = [
        busy(
            tomorrow,
            9,
            10,
            "meeting-1",
        ),
        busy(
            tomorrow,
            13,
            14,
            "meeting-2",
        ),
        busy(
            tomorrow,
            17,
            18,
            "meeting-3",
        ),
    ]

    result = find_focus_blocks(
        duration_minutes=180,
        window=window,
        buffer_config=BufferConfig(),
        busy_intervals=calendar_busy,
    )

    assert len(result) == 2

    assert result[0].start == dt(
        tomorrow,
        10,
    )

    assert result[0].end == dt(
        tomorrow,
        13,
    )

    assert result[0].duration_minutes == 180

    assert result[1].start == dt(
        tomorrow,
        14,
    )

    assert result[1].end == dt(
        tomorrow,
        17,
    )

    assert result[1].duration_minutes == 180


def test_three_hour_request_rejected_when_buffer_breaks_continuity():
    """
    A nominal 3-hour gap exists:

        10:00 -> 13:00

    But a 15-minute pre-event buffer is required before
    the 13:00 event.

    Effective focus time:

        10:00 -> 12:45

    Therefore the 3-hour request cannot fit.
    """

    tomorrow = 13

    window = DateTimeRange(
        start=dt(
            tomorrow,
            10,
        ),
        end=dt(
            tomorrow,
            14,
        ),
    )

    calendar_busy = [
        busy(
            tomorrow,
            13,
            14,
            "meeting-1",
        ),
    ]

    result = find_focus_blocks(
        duration_minutes=180,
        window=window,
        buffer_config=BufferConfig(
            before_minutes=15,
        ),
        busy_intervals=calendar_busy,
    )

    assert result == []


def test_focus_time_respects_scheduling_window():
    """
    Calendar has a large free period, but focus work is only
    allowed from 14:00 -> 18:00.
    """

    from windows import SchedulingWindow

    tomorrow = 13

    window = DateTimeRange(
        start=dt(
            tomorrow,
            9,
        ),
        end=dt(
            tomorrow,
            20,
        ),
    )

    scheduling_window = SchedulingWindow(
        name="coding",
        start_time="14:00",
        end_time="18:00",
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
            5,
            6,
        ],
    )

    result = find_focus_blocks(
        duration_minutes=180,
        window=window,
        buffer_config=BufferConfig(),
        busy_intervals=[],
        scheduling_window=scheduling_window,
        timezone=IST,
    )

    assert len(result) == 1

    assert result[0].start == dt(
        tomorrow,
        14,
    )

    assert result[0].end == dt(
        tomorrow,
        18,
    )

    assert result[0].duration_minutes == 240