from __future__ import annotations

from dataclasses import dataclass

from busy_intervals import BusyInterval
from datetime_utils import DateTimeRange


@dataclass(frozen=True)
class AvailabilityResult:
    """
    Result of checking whether a requested time range
    is available.

    conflicts contains every busy interval that overlaps
    the requested range.
    """

    available: bool
    requested_range: DateTimeRange
    conflicts: list[BusyInterval]


def check_availability(
    requested_range: DateTimeRange,
    busy_intervals: list[BusyInterval],
) -> AvailabilityResult:
    """
    Determine whether the requested range is free.

    Two intervals overlap when:

        busy.start < requested.end
        AND
        busy.end > requested.start

    Boundary touching is NOT considered an overlap.

    Example:

        Busy:       10:00 -> 11:00
        Requested:  11:00 -> 12:00

    Result:

        available = True
    """

    conflicts: list[BusyInterval] = []

    for busy in busy_intervals:

        if (
            busy.start < requested_range.end
            and busy.end > requested_range.start
        ):
            conflicts.append(busy)

    return AvailabilityResult(
        available=len(conflicts) == 0,
        requested_range=requested_range,
        conflicts=conflicts,
    )