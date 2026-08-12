from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from busy_intervals import BusyInterval
from buffers import BufferConfig, apply_buffers


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


# =========================================================
# 1. EXACT SPEC EXAMPLE
#
# 10:00 -> 11:00
# after = 15
#
# Expected:
# 10:00 -> 11:15
# =========================================================

def test_after_buffer_exact_spec_example():

    intervals = [
        busy(
            10,
            0,
            11,
            0,
            "event-1",
        )
    ]

    config = BufferConfig(
        after_minutes=15,
    )

    result = apply_buffers(
        intervals,
        config,
    )

    assert len(result) == 1

    assert result[0].start == dt(10, 0)

    assert result[0].end == dt(11, 15)

    assert result[0].source_event_ids == [
        "event-1"
    ]


# =========================================================
# 2. BEFORE BUFFER
# =========================================================

def test_before_buffer_pushes_start_earlier():

    intervals = [
        busy(
            10,
            0,
            11,
            0,
            "event-1",
        )
    ]

    config = BufferConfig(
        before_minutes=15,
    )

    result = apply_buffers(
        intervals,
        config,
    )

    assert result[0].start == dt(9, 45)

    assert result[0].end == dt(11, 0)


# =========================================================
# 3. TRAVEL BUFFER
# =========================================================

def test_travel_buffer_pushes_start_earlier():

    intervals = [
        busy(
            10,
            0,
            11,
            0,
            "event-1",
        )
    ]

    config = BufferConfig(
        travel_minutes=20,
    )

    result = apply_buffers(
        intervals,
        config,
    )

    assert result[0].start == dt(9, 40)

    assert result[0].end == dt(11, 0)


# =========================================================
# 4. PREPARATION BUFFER
# =========================================================

def test_preparation_buffer_pushes_start_earlier():

    intervals = [
        busy(
            10,
            0,
            11,
            0,
            "event-1",
        )
    ]

    config = BufferConfig(
        preparation_minutes=30,
    )

    result = apply_buffers(
        intervals,
        config,
    )

    assert result[0].start == dt(9, 30)

    assert result[0].end == dt(11, 0)


# =========================================================
# 5. MAX TRAVEL/PREPARATION
#
# Must use max(), NOT sum().
# =========================================================

def test_travel_and_preparation_use_maximum():

    intervals = [
        busy(
            10,
            0,
            11,
            0,
            "event-1",
        )
    ]

    config = BufferConfig(
        travel_minutes=20,
        preparation_minutes=30,
    )

    result = apply_buffers(
        intervals,
        config,
    )

    # max(20, 30) = 30
    assert result[0].start == dt(9, 30)

    assert result[0].end == dt(11, 0)


# =========================================================
# 6. BEFORE + TRAVEL + PREPARATION
# =========================================================

def test_before_and_max_pre_event_buffer_are_combined():

    intervals = [
        busy(
            10,
            0,
            11,
            0,
            "event-1",
        )
    ]

    config = BufferConfig(
        before_minutes=10,
        travel_minutes=20,
        preparation_minutes=30,
    )

    result = apply_buffers(
        intervals,
        config,
    )

    # 10 + max(20, 30) = 40
    assert result[0].start == dt(9, 20)

    assert result[0].end == dt(11, 0)


# =========================================================
# 7. AFTER + ALL PRE-EVENT BUFFERS
# =========================================================

def test_all_buffers_are_applied():

    intervals = [
        busy(
            10,
            0,
            11,
            0,
            "event-1",
        )
    ]

    config = BufferConfig(
        before_minutes=10,
        after_minutes=15,
        travel_minutes=20,
        preparation_minutes=30,
    )

    result = apply_buffers(
        intervals,
        config,
    )

    # Start:
    # 10:00 - 10 - max(20, 30)
    # = 09:20
    #
    # End:
    # 11:00 + 15
    # = 11:15

    assert result[0].start == dt(9, 20)

    assert result[0].end == dt(11, 15)


# =========================================================
# 8. ZERO BUFFER IS NO-OP
# =========================================================

def test_zero_buffer_is_noop():

    intervals = [
        busy(
            10,
            0,
            11,
            0,
            "event-1",
        ),
        busy(
            13,
            0,
            14,
            0,
            "event-2",
        ),
    ]

    original = [
        (
            interval.start,
            interval.end,
            interval.source_event_ids,
        )
        for interval in intervals
    ]

    result = apply_buffers(
        intervals,
        BufferConfig(),
    )

    assert [
        (
            interval.start,
            interval.end,
            interval.source_event_ids,
        )
        for interval in result
    ] == original


# =========================================================
# 9. ADJACENT MEETINGS MERGE AFTER BUFFERING
# =========================================================

def test_buffered_adjacent_meetings_are_remerged():

    intervals = [
        busy(
            10,
            0,
            11,
            0,
            "event-1",
        ),
        busy(
            11,
            20,
            12,
            0,
            "event-2",
        ),
    ]

    config = BufferConfig(
        before_minutes=15,
        after_minutes=15,
    )

    result = apply_buffers(
        intervals,
        config,
    )

    # Event 1:
    # 09:45 -> 11:15
    #
    # Event 2:
    # 11:05 -> 12:15
    #
    # They overlap and must merge.

    assert len(result) == 1

    assert result[0].start == dt(9, 45)

    assert result[0].end == dt(12, 15)

    assert set(
        result[0].source_event_ids
    ) == {
        "event-1",
        "event-2",
    }


# =========================================================
# 10. BUFFER DOES NOT MERGE EVENTS WHEN GAP REMAINS
# =========================================================

def test_buffered_events_remain_separate_when_gap_exists():

    intervals = [
        busy(
            10,
            0,
            11,
            0,
            "event-1",
        ),
        busy(
            12,
            0,
            13,
            0,
            "event-2",
        ),
    ]

    config = BufferConfig(
        before_minutes=10,
        after_minutes=10,
    )

    result = apply_buffers(
        intervals,
        config,
    )

    # Event 1:
    # 09:50 -> 11:10
    #
    # Event 2:
    # 11:50 -> 13:10
    #
    # 40 minute gap remains.

    assert len(result) == 2

    assert result[0].start == dt(9, 50)

    assert result[0].end == dt(11, 10)

    assert result[1].start == dt(11, 50)

    assert result[1].end == dt(13, 10)


# =========================================================
# 11. BUFFER COMPLETELY CONSUMES A GAP
# =========================================================

def test_buffer_can_completely_consume_gap():

    intervals = [
        busy(
            10,
            0,
            11,
            0,
            "event-1",
        ),
        busy(
            11,
            10,
            12,
            0,
            "event-2",
        ),
    ]

    config = BufferConfig(
        before_minutes=10,
        after_minutes=10,
    )

    result = apply_buffers(
        intervals,
        config,
    )

    # Event 1:
    # 09:50 -> 11:10
    #
    # Event 2:
    # 11:00 -> 12:10
    #
    # They overlap and merge.

    assert len(result) == 1

    assert result[0].start == dt(9, 50)

    assert result[0].end == dt(12, 10)

    assert set(
        result[0].source_event_ids
    ) == {
        "event-1",
        "event-2",
    }


# =========================================================
# 12. MULTIPLE EVENTS
# =========================================================

def test_multiple_events_are_buffered_independently():

    intervals = [
        busy(
            9,
            0,
            10,
            0,
            "event-1",
        ),
        busy(
            13,
            0,
            14,
            0,
            "event-2",
        ),
        busy(
            17,
            0,
            18,
            0,
            "event-3",
        ),
    ]

    config = BufferConfig(
        before_minutes=10,
        after_minutes=20,
    )

    result = apply_buffers(
        intervals,
        config,
    )

    assert len(result) == 3

    assert result[0].start == dt(8, 50)
    assert result[0].end == dt(10, 20)

    assert result[1].start == dt(12, 50)
    assert result[1].end == dt(14, 20)

    assert result[2].start == dt(16, 50)
    assert result[2].end == dt(18, 20)


# =========================================================
# 13. SOURCE EVENT IDS ARE PRESERVED
# =========================================================

def test_source_event_ids_are_preserved():

    intervals = [
        busy(
            10,
            0,
            11,
            0,
            "event-1",
        )
    ]

    result = apply_buffers(
        intervals,
        BufferConfig(
            before_minutes=15,
            after_minutes=15,
        ),
    )

    assert result[0].source_event_ids == [
        "event-1"
    ]


# =========================================================
# 14. INPUT IS NOT MUTATED
# =========================================================

def test_input_intervals_are_not_mutated():

    intervals = [
        busy(
            10,
            0,
            11,
            0,
            "event-1",
        )
    ]

    original_start = intervals[0].start

    original_end = intervals[0].end

    original_ids = list(
        intervals[0].source_event_ids
    )

    apply_buffers(
        intervals,
        BufferConfig(
            before_minutes=15,
            after_minutes=15,
        ),
    )

    assert intervals[0].start == original_start

    assert intervals[0].end == original_end

    assert (
        intervals[0].source_event_ids
        == original_ids
    )


# =========================================================
# 15. EMPTY INPUT
# =========================================================

def test_empty_input_returns_empty_output():

    result = apply_buffers(
        [],
        BufferConfig(
            before_minutes=15,
            after_minutes=15,
        ),
    )

    assert result == []


# =========================================================
# 16. NEGATIVE BEFORE BUFFER REJECTED
# =========================================================

def test_negative_before_buffer_rejected():

    with pytest.raises(ValidationError):

        BufferConfig(
            before_minutes=-1,
        )


# =========================================================
# 17. NEGATIVE AFTER BUFFER REJECTED
# =========================================================

def test_negative_after_buffer_rejected():

    with pytest.raises(ValidationError):

        BufferConfig(
            after_minutes=-1,
        )


# =========================================================
# 18. NEGATIVE TRAVEL BUFFER REJECTED
# =========================================================

def test_negative_travel_buffer_rejected():

    with pytest.raises(ValidationError):

        BufferConfig(
            travel_minutes=-1,
        )


# =========================================================
# 19. NEGATIVE PREPARATION BUFFER REJECTED
# =========================================================

def test_negative_preparation_buffer_rejected():

    with pytest.raises(ValidationError):

        BufferConfig(
            preparation_minutes=-1,
        )


# =========================================================
# 20. TIMEZONE-AWARE INTERVALS REMAIN AWARE
# =========================================================

def test_buffered_intervals_remain_timezone_aware():

    intervals = [
        busy(
            10,
            0,
            11,
            0,
            "event-1",
        )
    ]

    result = apply_buffers(
        intervals,
        BufferConfig(
            before_minutes=15,
            after_minutes=15,
        ),
    )

    assert result[0].start.tzinfo is not None

    assert result[0].end.tzinfo is not None

    assert result[0].start == dt(9, 45)

    assert result[0].end == dt(11, 15)


# =========================================================
# 21. START CAN CROSS MIDNIGHT
# =========================================================

def test_before_buffer_can_cross_midnight():

    intervals = [
        busy(
            0,
            10,
            1,
            0,
            "event-1",
        )
    ]

    result = apply_buffers(
        intervals,
        BufferConfig(
            before_minutes=30,
        ),
    )

    assert result[0].start == datetime(
        2026,
        8,
        11,
        23,
        40,
        tzinfo=IST,
    )

    assert result[0].end == dt(1, 0)


# =========================================================
# 22. END CAN CROSS MIDNIGHT
# =========================================================

def test_after_buffer_can_cross_midnight():

    intervals = [
        busy(
            23,
            30,
            23,
            50,
            "event-1",
        )
    ]

    result = apply_buffers(
        intervals,
        BufferConfig(
            after_minutes=30,
        ),
    )

    assert result[0].start == dt(23, 30)

    assert result[0].end == datetime(
        2026,
        8,
        13,
        0,
        20,
        tzinfo=IST,
    )