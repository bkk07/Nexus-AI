from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

from buffers import BufferConfig, apply_buffers
from busy_intervals import (
    BusyInterval,
    merge_busy_intervals,
)
from datetime_utils import DateTimeRange
from free_slots import find_free_slots
from models import TimeSlot
from windows import (
    SchedulingWindow,
    constrain_to_window,
)


def find_focus_blocks(
    *,
    duration_minutes: int,
    window: DateTimeRange,
    buffer_config: BufferConfig,
    busy_intervals: list[BusyInterval],
    scheduling_window: SchedulingWindow | None = None,
    timezone: ZoneInfo | None = None,
) -> list[TimeSlot]:
    """
    Find genuinely uninterrupted focus blocks.

    Phase 21 is intentionally a composition layer.

    Pipeline:

        Phase 8:
            find_free_slots()

        Phase 16:
            apply_buffers()

        Phase 17:
            constrain_to_window()

    A returned block must have uninterrupted capacity of at least
    duration_minutes after calendar buffers and scheduling-window
    constraints have been applied.

    The function does not create or modify calendar events.
    """

    if duration_minutes <= 0:
        raise ValueError(
            "duration_minutes must be positive."
        )

    if window.end <= window.start:
        raise ValueError(
            "window.end must be after window.start."
        )

    if (
        scheduling_window is not None
        and timezone is None
    ):
        raise ValueError(
            "timezone is required when "
            "scheduling_window is supplied."
        )

    # ---------------------------------------------------------
    # PHASE 16
    #
    # Apply existing calendar buffers.
    # ---------------------------------------------------------

    merged_busy = merge_busy_intervals(
        busy_intervals,
    )

    buffered_busy = apply_buffers(
        merged_busy,
        buffer_config,
    )

    # ---------------------------------------------------------
    # PHASE 17
    #
    # Restrict the requested DateTimeRange to the configured
    # scheduling window.
    #
    # Phase 17 currently supports one same-day window.
    # ---------------------------------------------------------

    effective_window = window

    if scheduling_window is not None:

        window_start_date = window.start.date()

        constrained = constrain_to_window(
            window_start_date,
            scheduling_window,
            timezone=timezone,
        )

        if constrained is None:
            return []

        constrained_start, constrained_end = (
            constrained
        )

        start = max(
            window.start,
            constrained_start,
        )

        end = min(
            window.end,
            constrained_end,
        )

        if end <= start:
            return []

        effective_window = DateTimeRange(
            start=start,
            end=end,
        )

    # ---------------------------------------------------------
    # PHASE 8
    #
    # Find free intervals after buffers and window
    # constraints.
    #
    # minimum_duration_minutes is intentionally set to
    # duration_minutes so that only genuinely uninterrupted
    # blocks capable of satisfying the complete request survive.
    # ---------------------------------------------------------

    focus_blocks = find_free_slots(
        window=effective_window,
        busy_intervals=buffered_busy,
        minimum_duration_minutes=duration_minutes,
    )

    # ---------------------------------------------------------
    # Defensive final filtering.
    #
    # find_free_slots already guarantees this, but keeping the
    # explicit condition makes the Phase 21 contract obvious:
    # every returned block must genuinely accommodate the
    # requested uninterrupted duration.
    # ---------------------------------------------------------

    return [
        slot
        for slot in focus_blocks
        if slot.duration_minutes
        >= duration_minutes
    ]