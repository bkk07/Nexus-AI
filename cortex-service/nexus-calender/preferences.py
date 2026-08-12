from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from buffers import BufferConfig
from busy_intervals import BusyInterval
from windows import SchedulingWindow, constrain_to_window


class UserPreferences(BaseModel):
    """
    User-specific scheduling preferences.

    Preferences are configuration only.
    They do not perform ranking or calendar operations.
    """

    preferred_study_window: SchedulingWindow | None = None

    preferred_meeting_window: SchedulingWindow | None = None

    minimum_focus_minutes: int = Field(
        default=30,
        gt=0,
    )

    buffer_config: BufferConfig = Field(
        default_factory=BufferConfig,
    )

    working_hours: SchedulingWindow

    blocked_periods: list[SchedulingWindow] = Field(
        default_factory=list,
    )


def resolve_minimum_duration(
    preferences: UserPreferences,
    requested_duration_minutes: int | None,
) -> int:
    """
    Resolve the minimum duration for a scheduling request.

    Explicitly requested duration takes priority.

    If the user did not provide a duration,
    minimum_focus_minutes is used.
    """

    if requested_duration_minutes is not None:

        if requested_duration_minutes <= 0:
            raise ValueError(
                "requested_duration_minutes "
                "must be positive."
            )

        return requested_duration_minutes

    return preferences.minimum_focus_minutes


def blocked_windows_to_busy_intervals(
    day: date,
    preferences: UserPreferences,
    *,
    timezone: ZoneInfo,
) -> list[BusyInterval]:
    """
    Convert user-defined blocked periods into
    BusyIntervals for a specific calendar day.

    Blocked periods are treated as unavailable time,
    even when there is no Google Calendar event there.
    """

    intervals: list[BusyInterval] = []

    for window in preferences.blocked_periods:

        constrained = constrain_to_window(
            day,
            window,
            timezone=timezone,
        )

        if constrained is None:
            continue

        start, end = constrained

        intervals.append(
            BusyInterval(
                start=start,
                end=end,
                source_event_ids=[],
            )
        )

    return intervals