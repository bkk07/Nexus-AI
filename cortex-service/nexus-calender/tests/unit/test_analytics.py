from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from analytics import (
    build_day_summary,
    build_week_summary,
    calculate_fragmentation_score,
)
from busy_intervals import BusyInterval
from models import EventSummary, TimeSlot


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


def event(
    event_id: str,
    start_hour: int,
    end_hour: int,
    title: str = "Meeting",
) -> EventSummary:

    return EventSummary(
        event_id=event_id,
        title=title,
        start=dt(start_hour),
        end=dt(end_hour),
    )


def slot(
    start_hour: int,
    end_hour: int,
) -> TimeSlot:

    start = dt(start_hour)
    end = dt(end_hour)

    return TimeSlot(
        start=start,
        end=end,
        duration_minutes=(
            end_hour - start_hour
        ) * 60,
    )


# =========================================================
# TEST 1
# Day summary matches hand-calculated values
# =========================================================

def test_day_summary_matches_hand_calculated_values():

    events = [
        event(
            "e1",
            9,
            10,
        ),
        event(
            "e2",
            14,
            16,
        ),
    ]

    busy_intervals = [
        BusyInterval(
            start=dt(9),
            end=dt(10),
            source_event_ids=["e1"],
        ),
        BusyInterval(
            start=dt(14),
            end=dt(16),
            source_event_ids=["e2"],
        ),
    ]

    free_slots = [
        slot(
            10,
            14,
        ),
        slot(
            16,
            18,
        ),
    ]

    summary = build_day_summary(
        date(2026, 8, 12),
        events,
        busy_intervals,
        free_slots,
    )

    assert summary.date == date(
        2026,
        8,
        12,
    )

    assert summary.event_count == 2

    assert summary.busy_minutes == 180

    assert summary.free_minutes == 360

    assert (
        summary.longest_free_slot_minutes
        == 240
    )

    assert summary.meeting_minutes == 180

    assert summary.fragmentation_score == 0.0


# =========================================================
# TEST 2
# Fragmentation increases with small gaps
# =========================================================

def test_fragmentation_increases_with_small_gaps():

    large_block = [
        slot(
            9,
            13,
        ),
    ]

    many_small_gaps = [
        TimeSlot(
            start=dt(9),
            end=dt(9, 15),
            duration_minutes=15,
        ),
        TimeSlot(
            start=dt(10),
            end=dt(10, 15),
            duration_minutes=15,
        ),
        TimeSlot(
            start=dt(11),
            end=dt(11, 15),
            duration_minutes=15,
        ),
    ]

    large_block_score = (
        calculate_fragmentation_score(
            large_block,
        )
    )

    small_gap_score = (
        calculate_fragmentation_score(
            many_small_gaps,
        )
    )

    assert large_block_score == 0.0

    assert small_gap_score == 1.0

    assert (
        small_gap_score
        > large_block_score
    )


# =========================================================
# TEST 3
# Zero-event day is still valid
# =========================================================

def test_zero_event_day_is_valid():

    summary = build_day_summary(
        date(2026, 8, 12),
        events=[],
        busy_intervals=[],
        free_slots=[
            slot(
                9,
                18,
            ),
        ],
    )

    assert summary.date == date(
        2026,
        8,
        12,
    )

    assert summary.event_count == 0

    assert summary.busy_minutes == 0

    assert summary.free_minutes == 540

    assert (
        summary.longest_free_slot_minutes
        == 540
    )

    assert summary.meeting_minutes == 0

    assert summary.fragmentation_score == 0.0


# =========================================================
# TEST 4
# Week summary identifies busiest and least busy day
# =========================================================

def test_week_summary_identifies_busiest_and_least_busy_day():

    day_one_events = [
        event(
            "m1",
            9,
            10,
        ),
    ]

    day_one_busy = [
        BusyInterval(
            start=dt(9),
            end=dt(10),
            source_event_ids=["m1"],
        ),
    ]

    day_one_free = [
        slot(
            10,
            18,
        ),
    ]

    day_two_events = [
        event(
            "m2",
            9,
            11,
        ),
        event(
            "m3",
            14,
            16,
        ),
    ]

    day_two_busy = [
        BusyInterval(
            start=dt(9),
            end=dt(11),
            source_event_ids=["m2"],
        ),
        BusyInterval(
            start=dt(14),
            end=dt(16),
            source_event_ids=["m3"],
        ),
    ]

    day_two_free = [
        slot(
            11,
            14,
        ),
        slot(
            16,
            18,
        ),
    ]

    summaries = [
        build_day_summary(
            date(2026, 8, 10),
            day_one_events,
            day_one_busy,
            day_one_free,
        ),
        build_day_summary(
            date(2026, 8, 11),
            day_two_events,
            day_two_busy,
            day_two_free,
        ),
    ]

    summary = build_week_summary(
        date(2026, 8, 10),
        summaries,
    )

    assert (
        summary.busiest_day
        == date(2026, 8, 11)
    )

    assert (
        summary.least_busy_day
        == date(2026, 8, 10)
    )

    assert summary.total_free_minutes == 780


# =========================================================
# TEST 5
# Invalid fragmentation threshold
# =========================================================

def test_negative_threshold_is_rejected():

    with pytest.raises(ValueError):

        calculate_fragmentation_score(
            [],
            0,
        )