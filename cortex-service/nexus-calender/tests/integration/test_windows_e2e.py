from datetime import date, datetime
from zoneinfo import ZoneInfo

from busy_intervals import BusyInterval
from datetime_utils import DateTimeRange
from free_slots import find_free_slots
from windows import (
    SchedulingWindow,
    constrain_to_window,
)


IST = ZoneInfo("Asia/Kolkata")


def test_empty_calendar_is_constrained_to_working_hours():

    day = date(2026, 8, 12)  # Wednesday

    window_config = SchedulingWindow(
        name="working_hours",
        start_time="09:00",
        end_time="21:00",
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
    )

    window = constrain_to_window(
        day,
        window_config,
        timezone=IST,
    )

    assert window is not None

    window_start, window_end = window

    # Empty calendar.
    busy_intervals = []

    slots = find_free_slots(
        window=DateTimeRange(
            start=window_start,
            end=window_end,
        ),
        busy_intervals=busy_intervals,
        minimum_duration_minutes=60,
    )

    assert len(slots) == 1

    assert slots[0].start == datetime(
        2026,
        8,
        12,
        9,
        0,
        tzinfo=IST,
    )

    assert slots[0].end == datetime(
        2026,
        8,
        12,
        21,
        0,
        tzinfo=IST,
    )

    assert slots[0].duration_minutes == 720


def test_early_morning_is_not_schedulable():

    day = date(2026, 8, 12)

    window_config = SchedulingWindow(
        name="working_hours",
        start_time="09:00",
        end_time="21:00",
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
    )

    window = constrain_to_window(
        day,
        window_config,
        timezone=IST,
    )

    assert window is not None

    window_start, window_end = window

    # The user asks for 02:00 -> 03:00.
    requested_range = DateTimeRange(
        start=datetime(
            2026,
            8,
            12,
            2,
            0,
            tzinfo=IST,
        ),
        end=datetime(
            2026,
            8,
            12,
            3,
            0,
            tzinfo=IST,
        ),
    )

    # 02:00 is outside the scheduling window.
    assert requested_range.end <= window_start

    assert requested_range.start < window_start

    assert requested_range.end <= window_start

    # Therefore it must not be considered a schedulable slot.
    assert not (
        requested_range.start >= window_start
        and requested_range.end <= window_end
    )


def test_valid_morning_slot_is_schedulable():

    day = date(2026, 8, 12)

    window_config = SchedulingWindow(
        name="working_hours",
        start_time="09:00",
        end_time="21:00",
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
    )

    window = constrain_to_window(
        day,
        window_config,
        timezone=IST,
    )

    assert window is not None

    window_start, window_end = window

    requested_range = DateTimeRange(
        start=datetime(
            2026,
            8,
            12,
            10,
            0,
            tzinfo=IST,
        ),
        end=datetime(
            2026,
            8,
            12,
            11,
            0,
            tzinfo=IST,
        ),
    )

    assert (
        requested_range.start >= window_start
    )

    assert (
        requested_range.end <= window_end
    )


def test_custom_personal_window_restricts_empty_calendar():

    day = date(2026, 8, 12)

    window_config = SchedulingWindow(
        name="personal_hours",
        start_time="13:00",
        end_time="18:00",
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
    )

    window = constrain_to_window(
        day,
        window_config,
        timezone=IST,
    )

    assert window is not None

    window_start, window_end = window

    slots = find_free_slots(
        window=DateTimeRange(
            start=window_start,
            end=window_end,
        ),
        busy_intervals=[],
        minimum_duration_minutes=60,
    )

    assert len(slots) == 1

    assert slots[0].start.hour == 13
    assert slots[0].end.hour == 18
    assert slots[0].duration_minutes == 300


def test_weekend_produces_no_schedulable_window():

    # Saturday
    day = date(2026, 8, 15)

    window_config = SchedulingWindow(
        name="working_hours",
        start_time="09:00",
        end_time="21:00",
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
    )

    window = constrain_to_window(
        day,
        window_config,
        timezone=IST,
    )

    assert window is None


def test_calendar_events_are_still_respected_inside_window():

    day = date(2026, 8, 12)

    window_config = SchedulingWindow(
        name="working_hours",
        start_time="09:00",
        end_time="21:00",
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
    )

    window = constrain_to_window(
        day,
        window_config,
        timezone=IST,
    )

    assert window is not None

    window_start, window_end = window

    busy = [
        BusyInterval(
            start=datetime(
                2026,
                8,
                12,
                10,
                0,
                tzinfo=IST,
            ),
            end=datetime(
                2026,
                8,
                12,
                11,
                0,
                tzinfo=IST,
            ),
            source_event_ids=[
                "event-1"
            ],
        )
    ]

    slots = find_free_slots(
        window=DateTimeRange(
            start=window_start,
            end=window_end,
        ),
        busy_intervals=busy,
        minimum_duration_minutes=60,
    )

    assert len(slots) == 2

    assert slots[0].start == datetime(
        2026,
        8,
        12,
        9,
        0,
        tzinfo=IST,
    )

    assert slots[0].end == datetime(
        2026,
        8,
        12,
        10,
        0,
        tzinfo=IST,
    )

    assert slots[1].start == datetime(
        2026,
        8,
        12,
        11,
        0,
        tzinfo=IST,
    )

    assert slots[1].end == datetime(
        2026,
        8,
        12,
        21,
        0,
        tzinfo=IST,
    )