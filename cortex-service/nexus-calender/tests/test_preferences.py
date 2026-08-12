from datetime import datetime

import pytest

from buffers import BufferConfig
from preferences import UserPreferences
from windows import SchedulingWindow

from datetime import date
from zoneinfo import ZoneInfo

from preferences import (
    blocked_windows_to_busy_intervals,
    resolve_minimum_duration,
)


IST = ZoneInfo("Asia/Kolkata")


def make_window(
    name: str,
    start: str,
    end: str,
    weekdays: list[int] | None = None,
) -> SchedulingWindow:
    return SchedulingWindow(
        name=name,
        start_time=start,
        end_time=end,
        applies_weekdays=(
            weekdays
            if weekdays is not None
            else [0, 1, 2, 3, 4]
        ),
    )


def test_default_minimum_focus_minutes():
    preferences = UserPreferences(
        working_hours=make_window(
            "working_hours",
            "09:00",
            "18:00",
        )
    )

    assert preferences.minimum_focus_minutes == 30


def test_preferred_study_window_is_stored():
    study_window = make_window(
        "study",
        "18:00",
        "22:00",
    )

    preferences = UserPreferences(
        preferred_study_window=study_window,
        working_hours=make_window(
            "working_hours",
            "09:00",
            "22:00",
        ),
    )

    assert (
        preferences.preferred_study_window
        == study_window
    )


def test_preferred_meeting_window_is_stored():
    meeting_window = make_window(
        "meetings",
        "10:00",
        "17:00",
    )

    preferences = UserPreferences(
        preferred_meeting_window=meeting_window,
        working_hours=make_window(
            "working_hours",
            "09:00",
            "18:00",
        ),
    )

    assert (
        preferences.preferred_meeting_window
        == meeting_window
    )


def test_custom_minimum_focus_minutes():
    preferences = UserPreferences(
        minimum_focus_minutes=90,
        working_hours=make_window(
            "working_hours",
            "09:00",
            "18:00",
        ),
    )

    assert preferences.minimum_focus_minutes == 90


def test_buffer_config_is_stored():
    buffer_config = BufferConfig(
        before_minutes=15,
        after_minutes=10,
        travel_minutes=5,
        preparation_minutes=20,
    )

    preferences = UserPreferences(
        buffer_config=buffer_config,
        working_hours=make_window(
            "working_hours",
            "09:00",
            "18:00",
        ),
    )

    assert preferences.buffer_config == buffer_config


def test_blocked_periods_are_stored():
    blocked = [
        make_window(
            "lunch",
            "13:00",
            "14:00",
        ),
        make_window(
            "personal",
            "17:00",
            "18:00",
        ),
    ]

    preferences = UserPreferences(
        blocked_periods=blocked,
        working_hours=make_window(
            "working_hours",
            "09:00",
            "18:00",
        ),
    )

    assert preferences.blocked_periods == blocked


def test_optional_preferences_can_be_missing():
    preferences = UserPreferences(
        working_hours=make_window(
            "working_hours",
            "09:00",
            "18:00",
        )
    )

    assert preferences.preferred_study_window is None
    assert preferences.preferred_meeting_window is None
    assert preferences.blocked_periods == []


@pytest.mark.parametrize(
    "minimum_focus_minutes",
    [0, -1, -30],
)
def test_invalid_minimum_focus_minutes_rejected(
    minimum_focus_minutes: int,
):
    with pytest.raises(ValueError):
        UserPreferences(
            minimum_focus_minutes=minimum_focus_minutes,
            working_hours=make_window(
                "working_hours",
                "09:00",
                "18:00",
            ),
        )


def test_preferences_do_not_modify_blocked_periods_between_instances():
    first = UserPreferences(
        working_hours=make_window(
            "working_hours",
            "09:00",
            "18:00",
        )
    )

    second = UserPreferences(
        working_hours=make_window(
            "working_hours",
            "09:00",
            "18:00",
        )
    )

    first.blocked_periods.append(
        make_window(
            "personal",
            "13:00",
            "14:00",
        )
    )

    assert len(first.blocked_periods) == 1
    assert second.blocked_periods == []


def test_explicit_duration_overrides_minimum_focus():

    preferences = UserPreferences(
        minimum_focus_minutes=60,
        working_hours=make_window(
            "working_hours",
            "09:00",
            "18:00",
        ),
    )

    result = resolve_minimum_duration(
        preferences,
        requested_duration_minutes=90,
    )

    assert result == 90


def test_minimum_focus_is_used_when_duration_missing():

    preferences = UserPreferences(
        minimum_focus_minutes=60,
        working_hours=make_window(
            "working_hours",
            "09:00",
            "18:00",
        ),
    )

    result = resolve_minimum_duration(
        preferences,
        requested_duration_minutes=None,
    )

    assert result == 60


def test_invalid_explicit_duration_is_rejected():

    preferences = UserPreferences(
        working_hours=make_window(
            "working_hours",
            "09:00",
            "18:00",
        ),
    )

    with pytest.raises(ValueError):

        resolve_minimum_duration(
            preferences,
            requested_duration_minutes=0,
        )


def test_blocked_period_becomes_busy_interval():

    blocked = make_window(
        "lunch",
        "13:00",
        "14:00",
    )

    preferences = UserPreferences(
        working_hours=make_window(
            "working_hours",
            "09:00",
            "18:00",
        ),
        blocked_periods=[
            blocked,
        ],
    )

    intervals = blocked_windows_to_busy_intervals(
        date(2026, 8, 12),
        preferences,
        timezone=IST,
    )

    assert len(intervals) == 1

    assert intervals[0].start.hour == 13
    assert intervals[0].start.minute == 0

    assert intervals[0].end.hour == 14
    assert intervals[0].end.minute == 0

    assert intervals[0].source_event_ids == []


def test_blocked_period_not_applied_on_wrong_weekday():

    blocked = SchedulingWindow(
        name="weekday_block",
        start_time="13:00",
        end_time="14:00",
        applies_weekdays=[0],
    )

    preferences = UserPreferences(
        working_hours=make_window(
            "working_hours",
            "09:00",
            "18:00",
        ),
        blocked_periods=[
            blocked,
        ],
    )

    # 2026-08-12 is Wednesday.
    intervals = blocked_windows_to_busy_intervals(
        date(2026, 8, 12),
        preferences,
        timezone=IST,
    )

    assert intervals == []