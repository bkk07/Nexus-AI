from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from buffers import BufferConfig
from busy_intervals import BusyInterval
from datetime_utils import DateTimeRange
from engine.focus_time import find_focus_blocks
from models import TimeSlot
from windows import SchedulingWindow


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


def make_range(
    start_hour: int,
    start_minute: int,
    end_hour: int,
    end_minute: int,
) -> DateTimeRange:
    return DateTimeRange(
        start=dt(
            start_hour,
            start_minute,
        ),
        end=dt(
            end_hour,
            end_minute,
        ),
    )


def busy(
    start_hour: int,
    start_minute: int,
    end_hour: int,
    end_minute: int,
    event_id: str,
) -> BusyInterval:
    return BusyInterval(
        start=dt(
            start_hour,
            start_minute,
        ),
        end=dt(
            end_hour,
            end_minute,
        ),
        source_event_ids=[event_id],
    )


def make_window(
    name: str,
    start: str,
    end: str,
) -> SchedulingWindow:
    return SchedulingWindow(
        name=name,
        start_time=start,
        end_time=end,
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
    )


def test_only_longest_gap_can_accommodate_focus_duration():
    """
    Requested duration is 3 hours.

    Free gaps:

        09:00 -> 10:00   = 60 min
        10:00 -> 14:00   = 240 min
        14:00 -> 15:00   = 60 min

    Only the 4-hour gap can accommodate 3 hours.
    """

    window = make_range(
        9,
        0,
        15,
        0,
    )

    busy_intervals = [
        busy(
            9,
            0,
            10,
            0,
            "event-1",
        ),
        busy(
            14,
            0,
            15,
            0,
            "event-2",
        ),
    ]

    result = find_focus_blocks(
        duration_minutes=180,
        window=window,
        buffer_config=BufferConfig(),
        busy_intervals=busy_intervals,
    )

    assert len(result) == 1

    assert result[0].start == dt(
        10,
        0,
    )

    assert result[0].end == dt(
        14,
        0,
    )

    assert result[0].duration_minutes == 240


def test_buffers_shrink_barely_sufficient_gap_below_requirement():
    """
    Without buffers:

        09:00 -> 12:00 = 180 minutes

    Requested:

        180 minutes

    Event after the gap:

        12:00 -> 13:00

    With a 15-minute pre-event buffer, the effective
    free time becomes:

        09:00 -> 11:45 = 165 minutes

    Therefore the 3-hour uninterrupted block must be rejected.
    """

    window = make_range(
        9,
        0,
        13,
        0,
    )

    busy_intervals = [
        busy(
            12,
            0,
            13,
            0,
            "event-1",
        ),
    ]

    result = find_focus_blocks(
        duration_minutes=180,
        window=window,
        buffer_config=BufferConfig(
            before_minutes=15,
        ),
        busy_intervals=busy_intervals,
    )

    assert result == []


def test_multiple_qualifying_focus_blocks_are_returned_sorted():
    """
    Two independent blocks can satisfy the request.

        09:00 -> 12:00 = 180 min
        14:00 -> 18:00 = 240 min

    Requested = 120 minutes.
    """

    window = make_range(
        9,
        0,
        18,
        0,
    )

    busy_intervals = [
        busy(
            12,
            0,
            14,
            0,
            "event-1",
        ),
    ]

    result = find_focus_blocks(
        duration_minutes=120,
        window=window,
        buffer_config=BufferConfig(),
        busy_intervals=busy_intervals,
    )

    assert len(result) == 2

    assert result[0].start == dt(
        9,
        0,
    )

    assert result[0].end == dt(
        12,
        0,
    )

    assert result[1].start == dt(
        14,
        0,
    )

    assert result[1].end == dt(
        18,
        0,
    )


def test_focus_blocks_are_subset_of_unbuffered_free_slots():
    """
    Phase 21 must never invent time.

    Every focus block must lie completely inside one of the
    original Phase 8 free slots.
    """

    from free_slots import find_free_slots

    window = make_range(
        9,
        0,
        18,
        0,
    )

    busy_intervals = [
        busy(
            12,
            0,
            13,
            0,
            "event-1",
        ),
        busy(
            16,
            0,
            17,
            0,
            "event-2",
        ),
    ]

    unbuffered = find_free_slots(
        window=window,
        busy_intervals=busy_intervals,
        minimum_duration_minutes=1,
    )

    focus = find_focus_blocks(
        duration_minutes=120,
        window=window,
        buffer_config=BufferConfig(),
        busy_intervals=busy_intervals,
    )

    for focus_slot in focus:

        assert any(
            free_slot.start
            <= focus_slot.start
            and focus_slot.end
            <= free_slot.end
            for free_slot in unbuffered
        )


def test_scheduling_window_removes_outside_focus_blocks():
    """
    Free time exists from 09:00 -> 18:00.

    Scheduling window:

        14:00 -> 18:00

    Requested focus duration:

        120 minutes

    Only the afternoon portion is eligible.
    """

    window = make_range(
        9,
        0,
        18,
        0,
    )

    scheduling_window = make_window(
        "focus",
        "14:00",
        "18:00",
    )

    result = find_focus_blocks(
        duration_minutes=120,
        window=window,
        buffer_config=BufferConfig(),
        busy_intervals=[],
        scheduling_window=scheduling_window,
        timezone=IST,
    )

    assert len(result) == 1

    assert result[0].start == dt(
        14,
        0,
    )

    assert result[0].end == dt(
        18,
        0,
    )


def test_non_applicable_weekday_returns_no_focus_blocks():
    """
    2026-08-12 is Wednesday.

    A Monday-only scheduling window must produce no result.
    """

    window = make_range(
        9,
        0,
        18,
        0,
    )

    monday_only = SchedulingWindow(
        name="monday",
        start_time="09:00",
        end_time="18:00",
        applies_weekdays=[
            0,
        ],
    )

    result = find_focus_blocks(
        duration_minutes=60,
        window=window,
        buffer_config=BufferConfig(),
        busy_intervals=[],
        scheduling_window=monday_only,
        timezone=IST,
    )

    assert result == []


def test_invalid_duration_is_rejected():
    window = make_range(
        9,
        0,
        18,
        0,
    )

    with pytest.raises(ValueError):
        find_focus_blocks(
            duration_minutes=0,
            window=window,
            buffer_config=BufferConfig(),
            busy_intervals=[],
        )


def test_invalid_window_is_rejected():
    with pytest.raises(ValueError):
        make_range(
            18,
            0,
            9,
            0,
        )


def test_scheduling_window_requires_timezone():
    window = make_range(
        9,
        0,
        18,
        0,
    )

    scheduling_window = make_window(
        "focus",
        "09:00",
        "18:00",
    )

    with pytest.raises(ValueError):
        find_focus_blocks(
            duration_minutes=60,
            window=window,
            buffer_config=BufferConfig(),
            busy_intervals=[],
            scheduling_window=scheduling_window,
        )