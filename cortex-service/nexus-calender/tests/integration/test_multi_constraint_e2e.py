from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from busy_intervals import BusyInterval
from datetime_utils import DateTimeRange
from engine.multi_constraint import (
    find_multi_constraint_slots,
)
from models import CalendarMultiConstraintRequest


IST = ZoneInfo("Asia/Kolkata")


def dt(
    hour: int,
    minute: int = 0,
) -> datetime:
    return datetime(
        2026,
        8,
        14,
        hour,
        minute,
        tzinfo=IST,
    )


def window(
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
# EXACT SPEC EXAMPLE 1
#
# "I need 2 hours for DSA tomorrow evening,
#  preferably after 6 PM, but not after 9 PM."
# =========================================================


def test_dsa_two_hours_evening_with_hard_9pm_bound():

    request = CalendarMultiConstraintRequest(
        duration_minutes=120,
        hard_start_time="17:00",
        hard_end_time="21:00",
        preferred_start_time="18:00",
        preferred_end_time="21:00",
        purpose="DSA",
    )

    result = find_multi_constraint_slots(
        request=request,
        window=window(
            9,
            22,
        ),
        busy_intervals=[
            busy(
                17,
                18,
            ),
        ],
    )

    assert result.status == "feasible"

    assert result.blocks

    selected = result.blocks[0]

    # Exactly two hours.
    assert (
        selected.duration_minutes
        == 120
    )

    # Hard constraint:
    # absolutely nothing after 21:00.
    assert selected.end <= dt(21)

    # Evening preference should be respected
    # when qualifying availability exists.
    assert selected.start.hour >= 18


# =========================================================
# EXACT SPEC EXAMPLE 2
#
# "Find me 3 hours for the project before Friday,
#  preferably in two uninterrupted blocks."
# =========================================================


def test_project_three_hours_before_friday_in_two_blocks():

    request = CalendarMultiConstraintRequest(
        duration_minutes=180,
        split_required=True,
        number_of_blocks=2,
        purpose="project",
        deadline=dt(22),
    )

    result = find_multi_constraint_slots(
        request=request,
        window=window(
            9,
            22,
        ),
        busy_intervals=[
            busy(
                11,
                12,
            ),
            busy(
                15,
                16,
            ),
        ],
    )

    assert result.status == "feasible"

    # Exactly two blocks.
    assert len(result.blocks) == 2

    # Exactly three hours total.
    total_duration = sum(
        block.duration_minutes
        for block in result.blocks
    )

    assert total_duration == 180

    # Each block is individually uninterrupted.
    for block in result.blocks:

        assert block.start < block.end

        actual_duration = int(
            (
                block.end
                - block.start
            ).total_seconds()
            // 60
        )

        assert (
            actual_duration
            == block.duration_minutes
        )

    # Deadline is hard.
    for block in result.blocks:
        assert block.end <= dt(22)


# =========================================================
# HARD CONSTRAINT MUST BE STRICT
# =========================================================


def test_hard_constraint_beats_soft_preference():

    request = CalendarMultiConstraintRequest(
        duration_minutes=60,
        hard_start_time="18:00",
        hard_end_time="21:00",
        preferred_start_time="20:00",
        preferred_end_time="22:00",
    )

    result = find_multi_constraint_slots(
        request=request,
        window=window(
            9,
            22,
        ),
        busy_intervals=[],
    )

    assert result.status == "feasible"

    for block in result.blocks:

        assert block.start >= dt(18)
        assert block.end <= dt(21)


# =========================================================
# SOFT PREFERENCE MAY LOSE IF NO PREFERRED
# SLOT EXISTS
# =========================================================


def test_soft_preference_does_not_make_request_infeasible():

    request = CalendarMultiConstraintRequest(
        duration_minutes=60,
        preferred_start_time="18:00",
        preferred_end_time="21:00",
    )

    result = find_multi_constraint_slots(
        request=request,
        window=window(
            14,
            17,
        ),
        busy_intervals=[],
    )

    assert result.status == "feasible"

    assert result.blocks

    assert (
        result.blocks[0].start
        == dt(14)
    )


# =========================================================
# INFEASIBLE COMPOUND REQUEST
# =========================================================


def test_compound_request_reports_infeasibility():

    request = CalendarMultiConstraintRequest(
        duration_minutes=180,
        hard_start_time="18:00",
        hard_end_time="19:00",
        purpose="DSA",
    )

    result = find_multi_constraint_slots(
        request=request,
        window=window(
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
# BUSY CALENDAR CONSTRAINTS
# =========================================================


def test_compound_request_respects_calendar_busy_intervals():

    request = CalendarMultiConstraintRequest(
        duration_minutes=120,
        hard_start_time="18:00",
        hard_end_time="21:00",
        preferred_start_time="18:00",
        preferred_end_time="21:00",
    )

    result = find_multi_constraint_slots(
        request=request,
        window=window(
            9,
            22,
        ),
        busy_intervals=[
            busy(
                18,
                19,
            ),
        ],
    )

    assert result.status == "feasible"

    selected = result.blocks[0]

    assert selected.start >= dt(19)
    assert selected.end <= dt(21)

    assert (
        selected.duration_minutes
        == 120
    )


# =========================================================
# PHASE COMPOSITION CHECK
# =========================================================


def test_phase24_returns_ranked_phase10_candidates():

    request = CalendarMultiConstraintRequest(
        duration_minutes=60,
        preferred_start_time="18:00",
        preferred_end_time="21:00",
    )

    result = find_multi_constraint_slots(
        request=request,
        window=window(
            9,
            22,
        ),
        busy_intervals=[
            busy(
                12,
                13,
            ),
            busy(
                16,
                17,
            ),
        ],
    )

    assert result.status == "feasible"

    assert result.ranked_slots

    scores = [
        candidate.score
        for candidate in result.ranked_slots
    ]

    assert scores == sorted(
        scores,
        reverse=True,
    )