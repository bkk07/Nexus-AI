from __future__ import annotations

from datetime import date
from typing import Sequence

from pydantic import BaseModel, Field

from models import EventSummary, TimeSlot


DEFAULT_USABLE_GAP_THRESHOLD_MINUTES = 30


class DaySummary(BaseModel):
    date: date
    event_count: int
    busy_minutes: int
    free_minutes: int
    longest_free_slot_minutes: int
    meeting_minutes: int
    fragmentation_score: float = Field(ge=0.0, le=1.0)


class WeekSummary(BaseModel):
    week_start: date
    day_summaries: list[DaySummary]
    least_busy_day: date
    busiest_day: date
    total_free_minutes: int


def _minutes_between(start, end) -> int:
    return int((end - start).total_seconds() // 60)


def calculate_fragmentation_score(
    free_slots: Sequence[TimeSlot],
    usable_threshold_minutes: int = DEFAULT_USABLE_GAP_THRESHOLD_MINUTES,
) -> float:
    """
    Calculate fragmentation as:

        number of free gaps below usable threshold
        -------------------------------------------
                 total number of free gaps

    A day with no free gaps has fragmentation 0.0.
    """
    if usable_threshold_minutes <= 0:
        raise ValueError("usable_threshold_minutes must be positive")

    if not free_slots:
        return 0.0

    small_gaps = sum(
        1
        for slot in free_slots
        if slot.duration_minutes < usable_threshold_minutes
    )

    return small_gaps / len(free_slots)


def build_day_summary(
    day: date,
    events: Sequence[EventSummary],
    busy_intervals,
    free_slots: Sequence[TimeSlot],
    usable_threshold_minutes: int = DEFAULT_USABLE_GAP_THRESHOLD_MINUTES,
) -> DaySummary:
    """
    Build a deterministic summary for one day.

    Busy/free values come from the already-computed Phase 6 and
    Phase 8 primitives. This function performs aggregation only.
    """

    busy_minutes = sum(
        _minutes_between(interval.start, interval.end)
        for interval in busy_intervals
    )

    free_minutes = sum(
        slot.duration_minutes
        for slot in free_slots
    )

    longest_free_slot_minutes = max(
        (slot.duration_minutes for slot in free_slots),
        default=0,
    )

    meeting_minutes = sum(
        _minutes_between(event.start, event.end)
        for event in events
    )

    fragmentation_score = calculate_fragmentation_score(
        free_slots,
        usable_threshold_minutes,
    )

    return DaySummary(
        date=day,
        event_count=len(events),
        busy_minutes=busy_minutes,
        free_minutes=free_minutes,
        longest_free_slot_minutes=longest_free_slot_minutes,
        meeting_minutes=meeting_minutes,
        fragmentation_score=fragmentation_score,
    )


def build_week_summary(
    week_start: date,
    day_summaries: Sequence[DaySummary],
) -> WeekSummary:
    """
    Aggregate seven DaySummary objects into a WeekSummary.
    """

    if not day_summaries:
        raise ValueError("day_summaries cannot be empty")

    busiest_day = max(
        day_summaries,
        key=lambda summary: (
            summary.busy_minutes,
            -summary.date.toordinal(),
        ),
    )

    least_busy_day = min(
        day_summaries,
        key=lambda summary: (
            summary.busy_minutes,
            summary.date.toordinal(),
        ),
    )

    total_free_minutes = sum(
        summary.free_minutes
        for summary in day_summaries
    )

    return WeekSummary(
        week_start=week_start,
        day_summaries=list(day_summaries),
        least_busy_day=least_busy_day.date,
        busiest_day=busiest_day.date,
        total_free_minutes=total_free_minutes,
    )