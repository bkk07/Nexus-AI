from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel, Field, field_validator

from busy_intervals import (
    BusyInterval,
    merge_busy_intervals,
)


class BufferConfig(BaseModel):
    """
    Configuration for calendar scheduling buffers.

    before_minutes:
        Additional blocked time before an event.

    after_minutes:
        Additional blocked time after an event.

    travel_minutes:
        Travel time required before an event.

    preparation_minutes:
        Preparation time required before an event.

    The effective additional pre-event buffer is:

        before_minutes
        + max(travel_minutes, preparation_minutes)
    """

    before_minutes: int = Field(
        default=0,
        ge=0,
    )

    after_minutes: int = Field(
        default=0,
        ge=0,
    )

    travel_minutes: int = Field(
        default=0,
        ge=0,
    )

    preparation_minutes: int = Field(
        default=0,
        ge=0,
    )


def apply_buffers(
    busy_intervals: list[BusyInterval],
    config: BufferConfig,
) -> list[BusyInterval]:
    """
    Expand busy intervals according to the configured buffers.

    For every interval:

        buffered_start =
            start
            - before_minutes
            - max(
                travel_minutes,
                preparation_minutes,
              )

        buffered_end =
            end
            + after_minutes

    After expansion, intervals are re-merged using the
    existing Phase 6 merge function.

    The input list is never modified.
    """

    if not busy_intervals:
        return []

    pre_event_buffer_minutes = (
        config.before_minutes
        + max(
            config.travel_minutes,
            config.preparation_minutes,
        )
    )

    buffered_intervals: list[BusyInterval] = []

    for interval in busy_intervals:

        if interval.end <= interval.start:
            raise ValueError(
                "Busy interval end must be after start."
            )

        buffered_start = (
            interval.start
            - timedelta(
                minutes=pre_event_buffer_minutes
            )
        )

        buffered_end = (
            interval.end
            + timedelta(
                minutes=config.after_minutes
            )
        )

        if buffered_end <= buffered_start:
            raise ValueError(
                "Buffered interval end must be "
                "after start."
            )

        buffered_intervals.append(
            BusyInterval(
                start=buffered_start,
                end=buffered_end,
                source_event_ids=list(
                    interval.source_event_ids
                ),
            )
        )

    # IMPORTANT:
    # Reuse Phase 6 merge logic.
    return merge_busy_intervals(
        buffered_intervals
    )