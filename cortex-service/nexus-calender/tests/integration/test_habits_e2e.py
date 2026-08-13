from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from engine.habits import (
    HabitDefinition,
    propose_habit_schedule,
)
from models import TimeSlot


IST = ZoneInfo("Asia/Kolkata")


def dt(
    day: int,
    hour: int,
) -> datetime:
    return datetime(
        2026,
        8,
        day,
        hour,
        0,
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


def test_schedule_dsa_for_two_hours_every_weekday():
    """
    User request:

        "Schedule DSA for 2 hours every weekday."

    Monday-Friday should each be considered independently.
    """

    habit = HabitDefinition(
        title="DSA",
        duration_minutes=120,
        applies_weekdays=[
            0,  # Monday
            1,  # Tuesday
            2,  # Wednesday
            3,  # Thursday
            4,  # Friday
        ],
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
        # Monday
        date(2026, 8, 10): [
            slot(10, 9, 12),
        ],

        # Tuesday
        date(2026, 8, 11): [
            slot(11, 10, 13),
        ],

        # Wednesday
        date(2026, 8, 12): [
            slot(12, 14, 16),
        ],

        # Thursday
        date(2026, 8, 13): [
            slot(13, 11, 14),
        ],

        # Friday
        date(2026, 8, 14): [
            slot(14, 15, 18),
        ],
    }

    result = propose_habit_schedule(
        habit,
        available_slots,
    )

    assert result.total_applicable_days == 5

    assert result.scheduled_days == 5

    assert result.unscheduled_days == 0

    assert len(result.days) == 5

    assert all(
        day.scheduled
        for day in result.days
    )

    assert all(
        day.slot is not None
        for day in result.days
    )

    assert all(
        day.slot.duration_minutes >= 120
        for day in result.days
        if day.slot is not None
    )


def test_weekend_is_not_scheduled_for_weekday_habit():

    habit = HabitDefinition(
        title="DSA",
        duration_minutes=120,
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
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
            slot(10, 9, 12),
        ],
        date(2026, 8, 11): [
            slot(11, 9, 12),
        ],
        date(2026, 8, 12): [
            slot(12, 9, 12),
        ],
        date(2026, 8, 13): [
            slot(13, 9, 12),
        ],
        date(2026, 8, 14): [
            slot(14, 9, 12),
        ],

        # Saturday
        date(2026, 8, 15): [
            slot(15, 9, 18),
        ],

        # Sunday
        date(2026, 8, 16): [
            slot(16, 9, 18),
        ],
    }

    result = propose_habit_schedule(
        habit,
        available_slots,
    )

    assert result.total_applicable_days == 5

    assert result.scheduled_days == 5

    assert all(
        day.date.weekday() < 5
        for day in result.days
    )


def test_one_conflicted_day_does_not_affect_other_days():

    habit = HabitDefinition(
        title="DSA",
        duration_minutes=120,
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
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
        # Monday — enough
        date(2026, 8, 10): [
            slot(10, 9, 12),
        ],

        # Tuesday — NOT enough
        date(2026, 8, 11): [
            slot(11, 10, 11),
        ],

        # Wednesday — enough
        date(2026, 8, 12): [
            slot(12, 13, 16),
        ],

        # Thursday — enough
        date(2026, 8, 13): [
            slot(13, 14, 17),
        ],

        # Friday — enough
        date(2026, 8, 14): [
            slot(14, 15, 18),
        ],
    }

    result = propose_habit_schedule(
        habit,
        available_slots,
    )

    assert result.total_applicable_days == 5

    assert result.scheduled_days == 4

    assert result.unscheduled_days == 1

    assert result.days[0].scheduled is True

    assert result.days[1].scheduled is False

    assert result.days[2].scheduled is True
    assert result.days[3].scheduled is True
    assert result.days[4].scheduled is True

    assert (
        result.days[1].date
        == date(2026, 8, 11)
    )


def test_preferred_window_is_used_for_each_recurring_day():

    habit = HabitDefinition(
        title="Evening DSA",
        duration_minutes=120,
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
        preferred_window_start=datetime.strptime(
            "18:00",
            "%H:%M",
        ).time(),
        preferred_window_end=datetime.strptime(
            "22:00",
            "%H:%M",
        ).time(),
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
        date(2026, 8, 10): [
            slot(10, 9, 12),
            slot(10, 19, 21),
        ],
        date(2026, 8, 11): [
            slot(11, 10, 12),
            slot(11, 18, 20),
        ],
        date(2026, 8, 12): [
            slot(12, 11, 13),
            slot(12, 19, 21),
        ],
        date(2026, 8, 13): [
            slot(13, 9, 11),
            slot(13, 18, 20),
        ],
        date(2026, 8, 14): [
            slot(14, 10, 12),
            slot(14, 19, 21),
        ],
    }

    result = propose_habit_schedule(
        habit,
        available_slots,
    )

    assert result.scheduled_days == 5

    for day in result.days:

        assert day.scheduled is True

        assert day.slot is not None

        assert day.slot.start.hour >= 18

        assert day.slot.end.hour <= 22


def test_habit_reports_summary_when_some_days_fail():

    habit = HabitDefinition(
        title="DSA",
        duration_minutes=120,
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
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
        date(2026, 8, 10): [
            slot(10, 9, 12),
        ],

        date(2026, 8, 11): [],

        date(2026, 8, 12): [
            slot(12, 9, 12),
        ],

        date(2026, 8, 13): [],

        date(2026, 8, 14): [
            slot(14, 9, 12),
        ],
    }

    result = propose_habit_schedule(
        habit,
        available_slots,
    )

    assert result.total_applicable_days == 5

    assert result.scheduled_days == 3

    assert result.unscheduled_days == 2

    assert result.summary == (
        "2 of 5 days could not be scheduled."
    )