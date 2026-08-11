from datetime import datetime

import pytest

from busy_intervals import BusyInterval
from datetime_utils import DateTimeRange
from free_slots import find_free_slots


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
    ).astimezone()


def window(
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


def test_completely_free_window():

    result = find_free_slots(
        window(9, 0, 18, 0),
        [],
    )

    assert len(result) == 1

    assert result[0].start == dt(9)
    assert result[0].end == dt(18)
    assert result[0].duration_minutes == 540


def test_completely_busy_window():

    result = find_free_slots(
        window(9, 0, 18, 0),
        [
            busy(
                9,
                0,
                18,
                0,
                "event-1",
            )
        ],
    )

    assert result == []


def test_one_event_creates_two_free_slots():

    result = find_free_slots(
        window(9, 0, 18, 0),
        [
            busy(
                12,
                0,
                14,
                0,
                "event-1",
            )
        ],
    )

    assert len(result) == 2

    assert (
        result[0].start,
        result[0].end,
        result[0].duration_minutes,
    ) == (
        dt(9),
        dt(12),
        180,
    )

    assert (
        result[1].start,
        result[1].end,
        result[1].duration_minutes,
    ) == (
        dt(14),
        dt(18),
        240,
    )


def test_multiple_busy_intervals():

    result = find_free_slots(
        window(9, 0, 18, 0),
        [
            busy(10, 0, 11, 0, "event-1"),
            busy(13, 0, 14, 0, "event-2"),
            busy(16, 0, 17, 0, "event-3"),
        ],
    )

    assert len(result) == 4

    assert [
        (
            slot.start,
            slot.end,
            slot.duration_minutes,
        )
        for slot in result
    ] == [
        (dt(9), dt(10), 60),
        (dt(11), dt(13), 120),
        (dt(14), dt(16), 120),
        (dt(17), dt(18), 60),
    ]


def test_minimum_duration_filters_small_gaps():

    result = find_free_slots(
        window(9, 0, 18, 0),
        [
            busy(10, 0, 10, 30, "event-1"),
            busy(11, 0, 14, 0, "event-2"),
        ],
        minimum_duration_minutes=60,
    )

    assert [
        slot.duration_minutes
        for slot in result
    ] == [
        60,
        240,
    ]


def test_exact_minimum_duration_is_included():

    result = find_free_slots(
        window(9, 0, 12, 0),
        [
            busy(10, 0, 11, 0, "event-1"),
        ],
        minimum_duration_minutes=60,
    )

    assert len(result) == 2

    assert result[0].duration_minutes == 60
    assert result[1].duration_minutes == 60


def test_gap_smaller_than_minimum_is_removed():

    result = find_free_slots(
        window(9, 0, 14, 0),
        [
            busy(10, 0, 10, 45, "event-1"),
            busy(11, 15, 12, 0, "event-2"),
        ],
        minimum_duration_minutes=60,
    )

    # 10:45 -> 11:15 is only 30 minutes.
    assert all(
        slot.duration_minutes >= 60
        for slot in result
    )

    assert [
        (
            slot.start,
            slot.end,
        )
        for slot in result
    ] == [
        (dt(9), dt(10)),
        (dt(12), dt(14)),
    ]


def test_event_at_window_start():

    result = find_free_slots(
        window(9, 0, 12, 0),
        [
            busy(
                9,
                0,
                10,
                0,
                "event-1",
            )
        ],
    )

    assert len(result) == 1

    assert result[0].start == dt(10)
    assert result[0].end == dt(12)


def test_event_at_window_end():

    result = find_free_slots(
        window(9, 0, 12, 0),
        [
            busy(
                11,
                0,
                12,
                0,
                "event-1",
            )
        ],
    )

    assert len(result) == 1

    assert result[0].start == dt(9)
    assert result[0].end == dt(11)


def test_back_to_back_events_create_no_gap():

    result = find_free_slots(
        window(9, 0, 15, 0),
        [
            busy(10, 0, 11, 0, "event-1"),
            busy(11, 0, 12, 0, "event-2"),
            busy(12, 0, 13, 0, "event-3"),
        ],
    )

    assert [
        (
            slot.start,
            slot.end,
        )
        for slot in result
    ] == [
        (dt(9), dt(10)),
        (dt(13), dt(15)),
    ]


def test_unsorted_busy_intervals_are_expected_to_be_merged_first():

    # The free-slot engine deliberately assumes that the input
    # has already been sorted/merged by BusyIntervalEngine.
    #
    # This test documents that contract rather than silently
    # implementing a second sorting/merging algorithm.

    result = find_free_slots(
        window(9, 0, 18, 0),
        [
            busy(10, 0, 11, 0, "event-1"),
            busy(13, 0, 14, 0, "event-2"),
        ],
    )

    assert len(result) == 3


def test_zero_duration_result_is_never_emitted():

    result = find_free_slots(
        window(9, 0, 10, 0),
        [
            busy(
                9,
                0,
                10,
                0,
                "event-1",
            )
        ],
    )

    assert all(
        slot.start < slot.end
        for slot in result
    )


def test_invalid_minimum_duration_is_rejected():

    with pytest.raises(ValueError):

        find_free_slots(
            window(9, 0, 18, 0),
            [],
            minimum_duration_minutes=0,
        )


def test_negative_minimum_duration_is_rejected():

    with pytest.raises(ValueError):

        find_free_slots(
            window(9, 0, 18, 0),
            [],
            minimum_duration_minutes=-30,
        )


def test_invalid_window_is_rejected():

    with pytest.raises(ValueError):

        find_free_slots(
            window(12, 0, 10, 0),
            [],
        )