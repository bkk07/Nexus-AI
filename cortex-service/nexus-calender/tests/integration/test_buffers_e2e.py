from datetime import datetime
from zoneinfo import ZoneInfo

from buffers import BufferConfig, apply_buffers
from busy_intervals import BusyInterval
from free_slots import find_free_slots
from datetime_utils import DateTimeRange


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
        start=dt(start_hour, start_minute),
        end=dt(end_hour, end_minute),
        source_event_ids=[event_id],
    )


def test_free_slot_shrinks_with_after_buffer():

    window = DateTimeRange(
        start=dt(9),
        end=dt(13),
    )

    events = [
        busy(
            10,
            0,
            11,
            0,
            "meeting-1",
        )
    ]

    # -----------------------------------------------------
    # Without buffers
    # -----------------------------------------------------

    unbuffered_slots = find_free_slots(
        window=window,
        busy_intervals=events,
        minimum_duration_minutes=1,
    )

    assert len(unbuffered_slots) == 2

    assert unbuffered_slots[0].start == dt(9)
    assert unbuffered_slots[0].end == dt(10)

    assert unbuffered_slots[1].start == dt(11)
    assert unbuffered_slots[1].end == dt(13)

    # -----------------------------------------------------
    # With 15-minute after buffer
    # -----------------------------------------------------

    buffered_intervals = apply_buffers(
        events,
        BufferConfig(
            after_minutes=15,
        ),
    )

    buffered_slots = find_free_slots(
        window=window,
        busy_intervals=buffered_intervals,
        minimum_duration_minutes=1,
    )

    assert len(buffered_slots) == 2

    assert buffered_slots[0].start == dt(9)
    assert buffered_slots[0].end == dt(10)

    assert buffered_slots[1].start == dt(11, 15)
    assert buffered_slots[1].end == dt(13)

    assert (
        buffered_slots[1].duration_minutes
        == 105
    )


def test_before_buffer_shrinks_preceding_free_slot():

    window = DateTimeRange(
        start=dt(9),
        end=dt(13),
    )

    events = [
        busy(
            11,
            0,
            12,
            0,
            "meeting-1",
        )
    ]

    unbuffered_slots = find_free_slots(
        window=window,
        busy_intervals=events,
        minimum_duration_minutes=1,
    )

    assert len(unbuffered_slots) == 2

    assert unbuffered_slots[0].start == dt(9)
    assert unbuffered_slots[0].end == dt(11)

    buffered_intervals = apply_buffers(
        events,
        BufferConfig(
            before_minutes=15,
        ),
    )

    buffered_slots = find_free_slots(
        window=window,
        busy_intervals=buffered_intervals,
        minimum_duration_minutes=1,
    )

    assert len(buffered_slots) == 2

    assert buffered_slots[0].start == dt(9)
    assert buffered_slots[0].end == dt(10, 45)

    assert buffered_slots[1].start == dt(12)
    assert buffered_slots[1].end == dt(13)


def test_buffer_completely_consumes_borderline_gap():

    window = DateTimeRange(
        start=dt(9),
        end=dt(13),
    )

    events = [
        busy(
            10,
            0,
            11,
            0,
            "meeting-1",
        ),
        busy(
            11,
            20,
            12,
            0,
            "meeting-2",
        ),
    ]

    # Without buffers there is a 20-minute gap.
    unbuffered_slots = find_free_slots(
        window=window,
        busy_intervals=events,
        minimum_duration_minutes=1,
    )

    assert any(
        slot.start == dt(11)
        and slot.end == dt(11, 20)
        for slot in unbuffered_slots
    )

    # 15-minute after + 15-minute before
    # completely consumes the 20-minute gap.
    buffered_intervals = apply_buffers(
        events,
        BufferConfig(
            before_minutes=15,
            after_minutes=15,
        ),
    )

    buffered_slots = find_free_slots(
        window=window,
        busy_intervals=buffered_intervals,
        minimum_duration_minutes=1,
    )

    assert all(
        not (
            slot.start >= dt(11)
            and slot.end <= dt(11, 20)
        )
        for slot in buffered_slots
    )

    # The buffered meetings should have merged.
    assert len(buffered_intervals) == 1

    assert buffered_intervals[0].start == dt(9, 45)
    assert buffered_intervals[0].end == dt(12, 15)


def test_zero_buffers_preserve_free_slots():

    window = DateTimeRange(
        start=dt(9),
        end=dt(13),
    )

    events = [
        busy(
            10,
            0,
            11,
            0,
            "meeting-1",
        )
    ]

    original_slots = find_free_slots(
        window=window,
        busy_intervals=events,
        minimum_duration_minutes=1,
    )

    buffered_intervals = apply_buffers(
        events,
        BufferConfig(),
    )

    buffered_slots = find_free_slots(
        window=window,
        busy_intervals=buffered_intervals,
        minimum_duration_minutes=1,
    )

    assert buffered_slots == original_slots


def test_travel_and_preparation_use_maximum_in_free_slot_calculation():

    window = DateTimeRange(
        start=dt(9),
        end=dt(13),
    )

    events = [
        busy(
            10,
            0,
            11,
            0,
            "meeting-1",
        )
    ]

    buffered_intervals = apply_buffers(
        events,
        BufferConfig(
            travel_minutes=20,
            preparation_minutes=30,
        ),
    )

    slots = find_free_slots(
        window=window,
        busy_intervals=buffered_intervals,
        minimum_duration_minutes=1,
    )

    # max(20, 30) = 30
    #
    # Meeting becomes:
    # 09:30 -> 11:00
    #
    # Therefore the first free slot is:
    # 11:00 -> 13:00

    assert len(slots) == 2

    assert slots[0].start == dt(9)
    assert slots[0].end == dt(9, 30)

    assert slots[1].start == dt(11)
    assert slots[1].end == dt(13)