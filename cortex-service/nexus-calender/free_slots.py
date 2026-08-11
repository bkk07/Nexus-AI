from __future__ import annotations

from datetime import datetime

from busy_intervals import BusyInterval
from datetime_utils import DateTimeRange
from models import TimeSlot


def find_free_slots(
    window: DateTimeRange,
    busy_intervals: list[BusyInterval],
    minimum_duration_minutes: int = 1,
) -> list[TimeSlot]:
    """
    Find all free intervals inside a scheduling window.

    busy_intervals must already be merged and sorted.

    A free slot is emitted only when its duration is at least
    minimum_duration_minutes.

    Boundary-touching intervals are handled naturally:

        window: 09:00 -> 18:00
        busy:   09:00 -> 10:00

        free starts at 10:00.
    """

    if minimum_duration_minutes <= 0:
        raise ValueError(
            "minimum_duration_minutes must be positive."
        )

    if window.end <= window.start:
        raise ValueError(
            "window.end must be after window.start."
        )

    minimum_duration = (
        minimum_duration_minutes
    )

    free_slots: list[TimeSlot] = []

    cursor = window.start

    for busy in busy_intervals:

        if busy.end <= busy.start:
            raise ValueError(
                "Busy interval end must be after start."
            )

        # Busy interval completely outside the window.
        if busy.end <= window.start:
            continue

        if busy.start >= window.end:
            break

        # Clamp the busy interval to the window.
        busy_start = max(
            busy.start,
            window.start,
        )

        busy_end = min(
            busy.end,
            window.end,
        )

        # There is a free gap before this busy interval.
        if busy_start > cursor:

            gap_minutes = int(
                (
                    busy_start - cursor
                ).total_seconds()
                // 60
            )

            if gap_minutes >= minimum_duration:

                free_slots.append(
                    TimeSlot(
                        start=cursor,
                        end=busy_start,
                        duration_minutes=gap_minutes,
                    )
                )

        # Move cursor forward.
        if busy_end > cursor:
            cursor = busy_end

    # Free time after the final busy interval.
    if cursor < window.end:

        gap_minutes = int(
            (
                window.end - cursor
            ).total_seconds()
            // 60
        )

        if gap_minutes >= minimum_duration:

            free_slots.append(
                TimeSlot(
                    start=cursor,
                    end=window.end,
                    duration_minutes=gap_minutes,
                )
            )

    return free_slots