from __future__ import annotations

from datetime import date, datetime, time
from pydantic import BaseModel, field_validator


class SchedulingWindow(BaseModel):
    """
    Defines when calendar time is considered schedulable.

    Weekday numbering:
        0 = Monday
        1 = Tuesday
        2 = Wednesday
        3 = Thursday
        4 = Friday
        5 = Saturday
        6 = Sunday
    """

    name: str
    start_time: str
    end_time: str
    applies_weekdays: list[int]

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: str,
    ) -> str:

        value = value.strip()

        if not value:
            raise ValueError(
                "Scheduling window name cannot be empty."
            )

        return value

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time(
        cls,
        value: str,
    ) -> str:

        value = value.strip()

        try:
            time.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                "Scheduling window time must be "
                "in HH:MM format."
            ) from exc

        # Phase 17 intentionally uses minute precision.
        parsed = time.fromisoformat(value)

        if parsed.second != 0 or parsed.microsecond != 0:
            raise ValueError(
                "Scheduling window time must use "
                "HH:MM precision."
            )

        return value

    @field_validator("applies_weekdays")
    @classmethod
    def validate_weekdays(
        cls,
        value: list[int],
    ) -> list[int]:

        if not value:
            raise ValueError(
                "applies_weekdays cannot be empty."
            )

        for weekday in value:

            if weekday < 0 or weekday > 6:
                raise ValueError(
                    "Weekdays must be between "
                    "0 and 6."
                )

        # Remove duplicates while preserving order.
        return list(dict.fromkeys(value))


def constrain_to_window(
    day: date,
    window: SchedulingWindow,
    *,
    timezone,
) -> tuple[datetime, datetime] | None:
    """
    Resolve a SchedulingWindow for a concrete date.

    Returns:
        (start_datetime, end_datetime)

    Returns None when the scheduling window does not
    apply to the supplied weekday.

    The returned datetimes are timezone-aware.
    """

    if day.weekday() not in window.applies_weekdays:
        return None

    start_time = time.fromisoformat(
        window.start_time
    )

    end_time = time.fromisoformat(
        window.end_time
    )

    start = datetime.combine(
        day,
        start_time,
        tzinfo=timezone,
    )

    end = datetime.combine(
        day,
        end_time,
        tzinfo=timezone,
    )

    # Phase 17 scheduling windows are same-day windows.
    # Overnight scheduling windows are intentionally
    # rejected rather than silently producing an invalid
    # scheduling range.
    if end <= start:
        raise ValueError(
            "Scheduling window end_time must be "
            "after start_time."
        )

    return start, end