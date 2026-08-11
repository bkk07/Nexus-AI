from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel
from models import EventSummary


class BusyInterval(BaseModel):
    """
    A continuous period during which the calendar is busy.

    source_event_ids contains every event that contributed
    to this merged interval.
    """

    start: datetime
    end: datetime
    source_event_ids: list[str] = []


def merge_busy_intervals(
    intervals: list[BusyInterval],
) -> list[BusyInterval]:
    """
    Sort and merge overlapping/touching busy intervals.

    Policy:
        - Overlapping intervals are merged.
        - Touching intervals are merged.
        - Result is sorted by start time.
        - source_event_ids from merged intervals are preserved.

    Example:

        09:00-10:00
        09:30-11:00

        becomes:

        09:00-11:00
    """

    if not intervals:
        return []

    # Work on sorted copies so the caller's list is never modified.
    sorted_intervals = sorted(
        intervals,
        key=lambda interval: interval.start,
    )

    merged: list[BusyInterval] = []

    for interval in sorted_intervals:

        # Defensive validation.
        if interval.end <= interval.start:
            raise ValueError(
                "Busy interval end must be after start."
            )

        if not merged:
            merged.append(
                BusyInterval(
                    start=interval.start,
                    end=interval.end,
                    source_event_ids=list(
                        interval.source_event_ids
                    ),
                )
            )
            continue

        current = merged[-1]

        # Overlap OR exact touching.
        if interval.start <= current.end:

            # Extend the interval if necessary.
            if interval.end > current.end:
                current.end = interval.end

            # Preserve all contributing event IDs.
            for event_id in interval.source_event_ids:
                if event_id not in current.source_event_ids:
                    current.source_event_ids.append(
                        event_id
                    )

        else:
            merged.append(
                BusyInterval(
                    start=interval.start,
                    end=interval.end,
                    source_event_ids=list(
                        interval.source_event_ids
                    ),
                )
            )

    return merged

def events_to_busy_intervals(
    events: list[EventSummary],
) -> list[BusyInterval]:
    """
    Convert calendar events into busy intervals.

    Each valid EventSummary becomes one BusyInterval.
    The resulting intervals are then merged.

    This function contains no LLM or Calendar API logic.
    """

    intervals: list[BusyInterval] = []

    for event in events:

        if event.end <= event.start:
            raise ValueError(
                f"Invalid event interval: "
                f"{event.event_id}"
            )

        intervals.append(
            BusyInterval(
                start=event.start,
                end=event.end,
                source_event_ids=[
                    event.event_id
                ],
            )
        )

    return merge_busy_intervals(
        intervals
    )