from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from engine.habits import (
    HabitDefinition,
    propose_habit_schedule,
)
from models import TimeSlot


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


def slot(
    day: int,
    start_hour: int,
    end_hour: int,
) -> TimeSlot:

    start = dt(
        day,
        start_hour,
    )

    end = dt(
        day,
        end_hour,
    )

    return TimeSlot(
        start=start,
        end=end,
        duration_minutes=(
            end_hour - start_hour
        ) * 60,
    )


def make_habit(
    *,
    start_date: date,
    end_date: date,
    duration_minutes: int = 120,
    weekdays: list[int] | None = None,
    preferred_start: time | None = None,
    preferred_end: time | None = None,
) -> HabitDefinition:

    if weekdays is None:
        weekdays = [
            0,
            1,
            2,
            3,
            4,
        ]

    return HabitDefinition(
        title="DSA",
        duration_minutes=duration_minutes,
        applies_weekdays=weekdays,
        preferred_window_start=preferred_start,
        preferred_window_end=preferred_end,
        start_date=start_date,
        end_date=end_date,
    )


def test_weekday_habit_skips_weekends():

    # 2026-08-10 = Monday
    # 2026-08-15 = Saturday
    # 2026-08-16 = Sunday

    habit = make_habit(
        start_date=date(
            2026,
            8,
            10,
        ),
        end_date=date(
            2026,
            8,
            16,
        ),
    )

    available_slots = {
        date(2026, 8, 10): [
            slot(10, 10, 13),
        ],
        date(2026, 8, 11): [
            slot(11, 10, 13),
        ],
        date(2026, 8, 12): [
            slot(12, 10, 13),
        ],
        date(2026, 8, 13): [
            slot(13, 10, 13),
        ],
        date(2026, 8, 14): [
            slot(14, 10, 13),
        ],
        date(2026, 8, 15): [
            slot(15, 10, 13),
        ],
        date(2026, 8, 16): [
            slot(16, 10, 13),
        ],
    }

    result = propose_habit_schedule(
        habit,
        available_slots,
    )

    assert result.total_applicable_days == 5
    assert result.scheduled_days == 5
    assert result.unscheduled_days == 0

    assert [
        item.date
        for item in result.days
    ] == [
        date(2026, 8, 10),
        date(2026, 8, 11),
        date(2026, 8, 12),
        date(2026, 8, 13),
        date(2026, 8, 14),
    ]


def test_weekend_inclusive_habit_includes_weekends():

    habit = make_habit(
        start_date=date(
            2026,
            8,
            14,
        ),
        end_date=date(
            2026,
            8,
            16,
        ),
        weekdays=[
            4,
            5,
            6,
        ],
    )

    available_slots = {
        date(2026, 8, 14): [
            slot(14, 10, 12),
        ],
        date(2026, 8, 15): [
            slot(15, 10, 12),
        ],
        date(2026, 8, 16): [
            slot(16, 10, 12),
        ],
    }

    result = propose_habit_schedule(
        habit,
        available_slots,
    )

    assert result.total_applicable_days == 3
    assert result.scheduled_days == 3

    assert [
        item.date
        for item in result.days
    ] == [
        date(2026, 8, 14),
        date(2026, 8, 15),
        date(2026, 8, 16),
    ]


def test_unschedulable_day_is_explicitly_reported():

    habit = make_habit(
        start_date=date(
            2026,
            8,
            10,
        ),
        end_date=date(
            2026,
            8,
            11,
        ),
    )

    available_slots = {
        date(2026, 8, 10): [
            slot(10, 10, 12),
        ],

        # Tuesday has only 60 minutes.
        date(2026, 8, 11): [
            slot(11, 10, 11),
        ],
    }

    result = propose_habit_schedule(
        habit,
        available_slots,
    )

    assert result.total_applicable_days == 2
    assert result.scheduled_days == 1
    assert result.unscheduled_days == 1

    monday = result.days[0]
    tuesday = result.days[1]

    assert monday.scheduled is True
    assert monday.slot is not None

    assert tuesday.scheduled is False
    assert tuesday.slot is None
    assert "no viable slot" in tuesday.reasons


def test_different_days_are_independent():

    habit = make_habit(
        start_date=date(
            2026,
            8,
            10,
        ),
        end_date=date(
            2026,
            8,
            12,
        ),
    )

    available_slots = {
        date(2026, 8, 10): [
            slot(10, 10, 12),
        ],

        # No availability Tuesday.
        date(2026, 8, 11): [],

        date(2026, 8, 12): [
            slot(12, 15, 17),
        ],
    }

    result = propose_habit_schedule(
        habit,
        available_slots,
    )

    assert result.total_applicable_days == 3
    assert result.scheduled_days == 2
    assert result.unscheduled_days == 1

    assert result.days[0].scheduled is True
    assert result.days[1].scheduled is False
    assert result.days[2].scheduled is True

    assert result.days[0].slot.start == dt(10, 10)
    assert result.days[2].slot.start == dt(12, 15)


def test_preferred_window_is_passed_to_best_slot():

    habit = make_habit(
        start_date=date(
            2026,
            8,
            12,
        ),
        end_date=date(
            2026,
            8,
            12,
        ),
        preferred_start=time(
            18,
            0,
        ),
        preferred_end=time(
            22,
            0,
        ),
    )

    available_slots = {
        date(2026, 8, 12): [
            slot(12, 10, 12),
            slot(12, 19, 21),
        ],
    }

    result = propose_habit_schedule(
        habit,
        available_slots,
    )

    assert result.scheduled_days == 1

    selected = result.days[0].slot

    assert selected is not None
    assert selected.start == dt(12, 19)
    assert selected.end == dt(12, 21)


def test_every_applicable_day_has_a_result():

    habit = make_habit(
        start_date=date(
            2026,
            8,
            10,
        ),
        end_date=date(
            2026,
            8,
            14,
        ),
    )

    available_slots = {
        date(2026, 8, 10): [],
        date(2026, 8, 11): [],
        date(2026, 8, 12): [],
        date(2026, 8, 13): [],
        date(2026, 8, 14): [],
    }

    result = propose_habit_schedule(
        habit,
        available_slots,
    )

    assert len(result.days) == 5

    assert [
        item.date
        for item in result.days
    ] == [
        date(2026, 8, 10),
        date(2026, 8, 11),
        date(2026, 8, 12),
        date(2026, 8, 13),
        date(2026, 8, 14),
    ]

    assert all(
        item.scheduled is False
        for item in result.days
    )


def test_summary_reports_unscheduled_days():

    habit = make_habit(
        start_date=date(
            2026,
            8,
            10,
        ),
        end_date=date(
            2026,
            8,
            12,
        ),
    )

    available_slots = {
        date(2026, 8, 10): [
            slot(10, 10, 12),
        ],

        date(2026, 8, 11): [],

        date(2026, 8, 12): [
            slot(12, 10, 12),
        ],
    }

    result = propose_habit_schedule(
        habit,
        available_slots,
    )

    assert result.summary == (
        "1 of 3 days could not be scheduled."
    )


def test_end_date_is_inclusive():

    habit = make_habit(
        start_date=date(
            2026,
            8,
            10,
        ),
        end_date=date(
            2026,
            8,
            10,
        ),
    )

    available_slots = {
        date(2026, 8, 10): [
            slot(10, 10, 12),
        ],
    }

    result = propose_habit_schedule(
        habit,
        available_slots,
    )

    assert result.total_applicable_days == 1
    assert result.scheduled_days == 1
    assert result.days[0].date == date(
        2026,
        8,
        10,
    )


def test_invalid_weekday_is_rejected():

    habit = make_habit(
        start_date=date(
            2026,
            8,
            10,
        ),
        end_date=date(
            2026,
            8,
            10,
        ),
        weekdays=[7],
    )

    with pytest.raises(ValueError):
        propose_habit_schedule(
            habit,
            {},
        )


def test_invalid_date_range_is_rejected():

    habit = make_habit(
        start_date=date(
            2026,
            8,
            12,
        ),
        end_date=date(
            2026,
            8,
            10,
        ),
    )

    with pytest.raises(ValueError):
        propose_habit_schedule(
            habit,
            {},
        )