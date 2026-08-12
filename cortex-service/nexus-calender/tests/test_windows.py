from datetime import date
from zoneinfo import ZoneInfo

import pytest

from windows import (
    SchedulingWindow,
    constrain_to_window,
)


IST = ZoneInfo("Asia/Kolkata")


def test_working_hours_window():

    window = SchedulingWindow(
        name="working_hours",
        start_time="09:00",
        end_time="21:00",
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
    )

    result = constrain_to_window(
        date(2026, 8, 12),  # Wednesday
        window,
        timezone=IST,
    )

    assert result is not None

    start, end = result

    assert start.isoformat() == (
        "2026-08-12T09:00:00+05:30"
    )

    assert end.isoformat() == (
        "2026-08-12T21:00:00+05:30"
    )


def test_personal_custom_window():

    window = SchedulingWindow(
        name="personal_hours",
        start_time="13:00",
        end_time="18:00",
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
    )

    result = constrain_to_window(
        date(2026, 8, 12),
        window,
        timezone=IST,
    )

    assert result is not None

    start, end = result

    assert start.hour == 13
    assert start.minute == 0

    assert end.hour == 18
    assert end.minute == 0


def test_weekday_only_window_returns_none_on_saturday():

    window = SchedulingWindow(
        name="working_hours",
        start_time="09:00",
        end_time="21:00",
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
    )

    # 2026-08-15 = Saturday
    result = constrain_to_window(
        date(2026, 8, 15),
        window,
        timezone=IST,
    )

    assert result is None


def test_weekday_only_window_returns_none_on_sunday():

    window = SchedulingWindow(
        name="working_hours",
        start_time="09:00",
        end_time="21:00",
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
    )

    # 2026-08-16 = Sunday
    result = constrain_to_window(
        date(2026, 8, 16),
        window,
        timezone=IST,
    )

    assert result is None


def test_weekend_window_can_be_explicitly_allowed():

    window = SchedulingWindow(
        name="weekend",
        start_time="10:00",
        end_time="14:00",
        applies_weekdays=[
            5,
            6,
        ],
    )

    saturday = constrain_to_window(
        date(2026, 8, 15),
        window,
        timezone=IST,
    )

    sunday = constrain_to_window(
        date(2026, 8, 16),
        window,
        timezone=IST,
    )

    assert saturday is not None
    assert sunday is not None


def test_blocked_hours_window():

    window = SchedulingWindow(
        name="blocked_hours",
        start_time="00:00",
        end_time="06:00",
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
            5,
            6,
        ],
    )

    result = constrain_to_window(
        date(2026, 8, 12),
        window,
        timezone=IST,
    )

    assert result is not None

    start, end = result

    assert start.hour == 0
    assert end.hour == 6


def test_custom_window_overrides_default():

    default_window = SchedulingWindow(
        name="working_hours",
        start_time="09:00",
        end_time="21:00",
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
    )

    custom_window = SchedulingWindow(
        name="custom",
        start_time="14:00",
        end_time="17:00",
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
    )

    default_result = constrain_to_window(
        date(2026, 8, 12),
        default_window,
        timezone=IST,
    )

    custom_result = constrain_to_window(
        date(2026, 8, 12),
        custom_window,
        timezone=IST,
    )

    assert default_result is not None
    assert custom_result is not None

    assert default_result != custom_result

    assert custom_result[0].hour == 14
    assert custom_result[1].hour == 17


def test_invalid_weekday_is_rejected():

    with pytest.raises(ValueError):

        SchedulingWindow(
            name="invalid",
            start_time="09:00",
            end_time="17:00",
            applies_weekdays=[7],
        )


def test_empty_weekday_list_is_rejected():

    with pytest.raises(ValueError):

        SchedulingWindow(
            name="invalid",
            start_time="09:00",
            end_time="17:00",
            applies_weekdays=[],
        )


def test_invalid_time_is_rejected():

    with pytest.raises(ValueError):

        SchedulingWindow(
            name="invalid",
            start_time="25:00",
            end_time="17:00",
            applies_weekdays=[0],
        )


def test_seconds_are_rejected():

    with pytest.raises(ValueError):

        SchedulingWindow(
            name="invalid",
            start_time="09:30:15",
            end_time="17:00",
            applies_weekdays=[0],
        )


def test_empty_name_is_rejected():

    with pytest.raises(ValueError):

        SchedulingWindow(
            name="   ",
            start_time="09:00",
            end_time="17:00",
            applies_weekdays=[0],
        )


def test_overnight_window_is_rejected():

    window = SchedulingWindow(
        name="overnight",
        start_time="22:00",
        end_time="06:00",
        applies_weekdays=[0],
    )

    with pytest.raises(ValueError):

        constrain_to_window(
            date(2026, 8, 10),
            window,
            timezone=IST,
        )