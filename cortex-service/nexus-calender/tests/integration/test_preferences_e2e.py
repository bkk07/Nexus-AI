from datetime import datetime, time
from zoneinfo import ZoneInfo

from best_slot import BestSlotService
from datetime_utils import DateTimeRange
from free_slots import find_free_slots
from busy_intervals import merge_busy_intervals
from models import TimeSlot
from preferences import (
    UserPreferences,
    blocked_windows_to_busy_intervals,
    resolve_minimum_duration,
)
from windows import SchedulingWindow


IST = ZoneInfo("Asia/Kolkata")


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


def make_slot(
    start_hour: int,
    end_hour: int,
) -> TimeSlot:

    start = datetime(
        2026,
        8,
        12,
        start_hour,
        tzinfo=IST,
    )

    end = datetime(
        2026,
        8,
        12,
        end_hour,
        tzinfo=IST,
    )

    return TimeSlot(
        start=start,
        end=end,
        duration_minutes=(
            end_hour - start_hour
        ) * 60,
    )


# =========================================================
# TEST 1
# Preferred study window changes ranking
# =========================================================

def test_evening_study_preference_changes_ranking():

    preferences = UserPreferences(
        preferred_study_window=make_window(
            "study",
            "18:00",
            "22:00",
        ),
        working_hours=make_window(
            "working_hours",
            "09:00",
            "22:00",
        ),
    )

    morning = make_slot(
        10,
        11,
    )

    evening = make_slot(
        19,
        20,
    )

    service = BestSlotService()

    ranked = service.rank_slots(
        slots=[
            morning,
            evening,
        ],
        requested_duration_minutes=60,
        preferred_window_start=time(18, 0),
        preferred_window_end=time(22, 0),
    )

    assert ranked[0].slot == evening
    assert ranked[1].slot == morning

    assert (
        ranked[0].score
        > ranked[1].score
    )


# =========================================================
# TEST 2
# Without preference, earlier slot wins tie
# =========================================================

def test_without_preference_earlier_slot_wins_tie():

    morning = make_slot(
        10,
        11,
    )

    evening = make_slot(
        19,
        20,
    )

    service = BestSlotService()

    ranked = service.rank_slots(
        slots=[
            morning,
            evening,
        ],
        requested_duration_minutes=60,
    )

    assert ranked[0].slot == morning


# =========================================================
# TEST 3
# Minimum focus duration
# =========================================================

def test_minimum_focus_changes_required_duration():

    preferences = UserPreferences(
        minimum_focus_minutes=90,
        working_hours=make_window(
            "working_hours",
            "09:00",
            "22:00",
        ),
    )

    duration = resolve_minimum_duration(
        preferences,
        requested_duration_minutes=None,
    )

    assert duration == 90


# =========================================================
# TEST 4
# Explicit duration overrides minimum focus
# =========================================================

def test_explicit_duration_overrides_focus_preference():

    preferences = UserPreferences(
        minimum_focus_minutes=90,
        working_hours=make_window(
            "working_hours",
            "09:00",
            "22:00",
        ),
    )

    duration = resolve_minimum_duration(
        preferences,
        requested_duration_minutes=45,
    )

    assert duration == 45


# =========================================================
# TEST 5
# Blocked period removes free time
# =========================================================

def test_blocked_period_removes_free_time():

    preferences = UserPreferences(
        working_hours=make_window(
            "working_hours",
            "09:00",
            "18:00",
        ),
        blocked_periods=[
            make_window(
                "lunch",
                "13:00",
                "14:00",
            ),
        ],
    )

    blocked = blocked_windows_to_busy_intervals(
        datetime(
            2026,
            8,
            12,
        ).date(),
        preferences,
        timezone=IST,
    )

    window = DateTimeRange(
        start=datetime(
            2026,
            8,
            12,
            9,
            tzinfo=IST,
        ),
        end=datetime(
            2026,
            8,
            12,
            18,
            tzinfo=IST,
        ),
    )

    merged = merge_busy_intervals(
        blocked
    )

    slots = find_free_slots(
        window=window,
        busy_intervals=merged,
        minimum_duration_minutes=30,
    )

    assert len(slots) == 2

    assert slots[0].start.hour == 9
    assert slots[0].end.hour == 13

    assert slots[1].start.hour == 14
    assert slots[1].end.hour == 18