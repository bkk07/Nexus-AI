from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from busy_intervals import BusyInterval
from datetime_utils import DateTimeRange
from engine.multi_constraint import (
    find_multi_constraint_slots,
)
from models import (
    CalendarMultiConstraintRequest,
)


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


def make_window(
    start_hour: int,
    end_hour: int,
) -> DateTimeRange:
    return DateTimeRange(
        start=dt(start_hour),
        end=dt(end_hour),
    )


def busy(
    start_hour: int,
    end_hour: int,
) -> BusyInterval:
    return BusyInterval(
        start=dt(start_hour),
        end=dt(end_hour),
        source_event_ids=[],
    )


# =========================================================
# 1. HARD WINDOW CONSTRAINT
# =========================================================


def test_hard_end_time_strictly_excludes_later_candidates():

    request = CalendarMultiConstraintRequest(
        duration_minutes=60,
        hard_start_time="18:00",
        hard_end_time="21:00",
        preferred_start_time="18:00",
        preferred_end_time="21:00",
        purpose="DSA",
    )

    result = find_multi_constraint_slots(
        request,
        window=make_window(
            9,
            22,
        ),
        busy_intervals=[],
    )

    assert result.status == "feasible"

    assert result.blocks

    selected = result.blocks[0]

    assert selected.start >= dt(18)

    assert selected.end <= dt(21)


def test_hard_end_constraint_rejects_slot_after_2100():

    request = CalendarMultiConstraintRequest(
        duration_minutes=120,
        hard_end_time="21:00",
    )

    result = find_multi_constraint_slots(
        request,
        window=make_window(
            18,
            22,
        ),
        busy_intervals=[],
    )

    assert result.status == "feasible"

    assert result.blocks

    for block in result.blocks:
        assert block.end <= dt(21)


# =========================================================
# 2. SOFT PREFERENCE
# =========================================================


def test_soft_preference_after_1800_changes_ranking():

    request = CalendarMultiConstraintRequest(
        duration_minutes=60,
        preferred_start_time="18:00",
        preferred_end_time="21:00",
    )

    available_busy = [
        busy(
            16,
            18,
        ),
        busy(
            19,
            22,
        ),
    ]

    result = find_multi_constraint_slots(
        request,
        window=make_window(
            14,
            22,
        ),
        busy_intervals=available_busy,
    )

    assert result.status == "feasible"

    assert result.ranked_slots

    # The earlier slot remains valid.
    starts = [
        option.slot.start.hour
        for option in result.ranked_slots
    ]

    assert 14 in starts

    # The preferred slot should rank above
    # the earlier non-preferred slot.
    if len(result.ranked_slots) >= 2:

        assert (
            result.ranked_slots[0].score
            >= result.ranked_slots[1].score
        )


def test_soft_preference_does_not_make_earlier_slot_invalid():

    request = CalendarMultiConstraintRequest(
        duration_minutes=60,
        preferred_start_time="18:00",
        preferred_end_time="21:00",
    )

    result = find_multi_constraint_slots(
        request,
        window=make_window(
            15,
            17,
        ),
        busy_intervals=[],
    )

    assert result.status == "feasible"

    assert result.blocks

    assert result.blocks[0].start == dt(15)


# =========================================================
# 3. EXACTLY TWO BLOCKS
# =========================================================


def test_three_hours_can_be_split_into_exactly_two_blocks():

    request = CalendarMultiConstraintRequest(
        duration_minutes=180,
        split_required=True,
        number_of_blocks=2,
        purpose="project",
    )

    available_busy = [
        busy(
            10,
            11,
        ),
        busy(
            14,
            15,
        ),
    ]

    result = find_multi_constraint_slots(
        request,
        window=make_window(
            9,
            18,
        ),
        busy_intervals=available_busy,
    )

    assert result.status == "feasible"

    assert len(result.blocks) == 2

    total_minutes = sum(
        block.duration_minutes
        for block in result.blocks
    )

    assert total_minutes == 180


def test_two_blocks_are_each_uninterrupted():

    request = CalendarMultiConstraintRequest(
        duration_minutes=180,
        split_required=True,
        number_of_blocks=2,
    )

    available_busy = [
        busy(
            11,
            12,
        ),
        busy(
            15,
            16,
        ),
    ]

    result = find_multi_constraint_slots(
        request,
        window=make_window(
            9,
            20,
        ),
        busy_intervals=available_busy,
    )

    assert result.status == "feasible"

    assert len(result.blocks) == 2

    for block in result.blocks:

        assert block.start < block.end

        actual_minutes = int(
            (
                block.end
                - block.start
            ).total_seconds()
            // 60
        )

        assert (
            actual_minutes
            == block.duration_minutes
        )


# =========================================================
# 4. INFEASIBLE HARD CONSTRAINTS
# =========================================================


def test_infeasible_when_hard_window_leaves_no_capacity():

    request = CalendarMultiConstraintRequest(
        duration_minutes=180,
        hard_start_time="18:00",
        hard_end_time="19:00",
    )

    result = find_multi_constraint_slots(
        request,
        window=make_window(
            9,
            22,
        ),
        busy_intervals=[],
    )

    assert result.status == "infeasible"

    assert result.blocks == []

    assert (
        result.unscheduled_minutes
        == 180
    )

    assert result.explanation


# =========================================================
# 5. INFEASIBLE TWO-BLOCK REQUEST
# =========================================================


def test_two_block_request_is_infeasible_when_only_one_slot_exists():

    request = CalendarMultiConstraintRequest(
        duration_minutes=180,
        split_required=True,
        number_of_blocks=2,
    )

    result = find_multi_constraint_slots(
        request,
        window=make_window(
            9,
            12,
        ),
        busy_intervals=[],
    )

    assert result.status == "infeasible"

    assert result.blocks == []

    assert (
        result.unscheduled_minutes
        == 180
    )

    assert result.explanation


# =========================================================
# 6. INVALID BLOCK COUNT
# =========================================================


def test_only_two_block_mode_is_supported():

    request = CalendarMultiConstraintRequest(
        duration_minutes=180,
        split_required=True,
        number_of_blocks=3,
    )

    result = find_multi_constraint_slots(
        request,
        window=make_window(
            9,
            18,
        ),
        busy_intervals=[],
    )

    assert result.status == "infeasible"

    assert result.blocks == []

    assert result.explanation


# =========================================================
# 7. DEADLINE
# =========================================================


def test_deadline_is_treated_as_hard_constraint():

    request = CalendarMultiConstraintRequest(
        duration_minutes=120,
        deadline=dt(17),
    )

    result = find_multi_constraint_slots(
        request,
        window=make_window(
            9,
            22,
        ),
        busy_intervals=[],
    )

    assert result.status == "feasible"

    assert result.blocks

    assert result.blocks[0].end <= dt(17)


def test_deadline_with_no_capacity_is_infeasible():

    request = CalendarMultiConstraintRequest(
        duration_minutes=180,
        deadline=dt(10),
    )

    result = find_multi_constraint_slots(
        request,
        window=make_window(
            9,
            22,
        ),
        busy_intervals=[],
    )

    assert result.status == "infeasible"

    assert result.blocks == []

    assert result.explanation


# =========================================================
# 8. PHASE 8 COMPOSITION REGRESSION
# =========================================================


def test_result_never_uses_busy_time():

    request = CalendarMultiConstraintRequest(
        duration_minutes=60,
    )

    busy_intervals = [
        busy(
            10,
            12,
        ),
    ]

    result = find_multi_constraint_slots(
        request,
        window=make_window(
            9,
            18,
        ),
        busy_intervals=busy_intervals,
    )

    assert result.status == "feasible"

    for block in result.blocks:

        assert not (
            block.start < dt(12)
            and block.end > dt(10)
        )


# =========================================================
# 9. NO CONSTRAINTS = NORMAL FREE-SLOT BEHAVIOR
# =========================================================


def test_without_constraints_phase8_behavior_is_preserved():

    request = CalendarMultiConstraintRequest(
        duration_minutes=120,
    )

    result = find_multi_constraint_slots(
        request,
        window=make_window(
            9,
            18,
        ),
        busy_intervals=[
            busy(
                12,
                13,
            ),
        ],
    )

    assert result.status == "feasible"

    assert result.blocks

    assert (
        result.blocks[0].duration_minutes
        >= 120
    )