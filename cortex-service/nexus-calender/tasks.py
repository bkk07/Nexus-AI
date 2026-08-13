from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Literal

from pydantic import BaseModel, Field

from models import TimeSlot
from windows import SchedulingWindow


class Task(BaseModel):
    """
    A scheduling task.

    Tasks are separate from Google Calendar events.
    This model contains only scheduling requirements.
    """

    title: str = Field(min_length=1)

    duration_minutes: int = Field(
        gt=0,
    )

    deadline: date | None = None

    priority: Literal[
        "low",
        "medium",
        "high",
    ] = "medium"

    preferred_window: SchedulingWindow | None = None

    splittable: bool = False


class ProposedBlock(BaseModel):
    """
    One proposed calendar block for a task.
    """

    task_title: str

    slot: TimeSlot


class TaskScheduleProposal(BaseModel):
    """
    Result of task scheduling.

    This is only a proposal.
    It does NOT create or modify Google Calendar events.
    """

    blocks: list[ProposedBlock] = Field(
        default_factory=list,
    )

    unscheduled_minutes: int = Field(
        ge=0,
    )

    status: Literal[
        "fully_scheduled",
        "partially_scheduled",
        "insufficient_capacity",
    ]


_PRIORITY_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
}


def _slot_minutes(
    slot: TimeSlot,
) -> int:
    """
    Return the duration of a TimeSlot in minutes.

    Prefer the actual datetime values instead of trusting a
    duplicated duration field.
    """

    return int(
        (
            slot.end
            - slot.start
        ).total_seconds()
        // 60
    )


def _slot_before_deadline(
    slot: TimeSlot,
    deadline: date | None,
) -> bool:
    """
    Check whether the proposed slot is allowed by the task deadline.

    A deadline is treated as inclusive for the calendar date.
    """

    if deadline is None:
        return True

    return slot.start.date() <= deadline


def _parse_window_time(
    value: str | time,
) -> time:
    """
    Convert a SchedulingWindow time value into datetime.time.

    SchedulingWindow stores times as strings such as:
        "18:00"

    This helper also accepts an already-created time object.
    """

    if isinstance(value, time):
        return value

    return time.fromisoformat(value)


def _slot_matches_preference(
    slot: TimeSlot,
    preferred_window: SchedulingWindow | None,
) -> bool:
    """
    Check whether a slot lies completely inside the preferred
    scheduling window.

    If no preference exists, every slot matches.

    Supports both normal daytime windows and overnight windows.
    """

    if preferred_window is None:
        return True

    start_time = (
        slot.start
        .timetz()
        .replace(
            tzinfo=None,
        )
    )

    end_time = (
        slot.end
        .timetz()
        .replace(
            tzinfo=None,
        )
    )

    preferred_start = _parse_window_time(
        preferred_window.start_time,
    )

    preferred_end = _parse_window_time(
        preferred_window.end_time,
    )

    # Normal daytime window.
    if preferred_start <= preferred_end:
        return (
            start_time >= preferred_start
            and end_time <= preferred_end
        )

    # Overnight window.
    return (
        start_time >= preferred_start
        or end_time <= preferred_end
    )


def _preferred_candidate_slot(
    slot: TimeSlot,
    preferred_window: SchedulingWindow | None,
    required_minutes: int,
) -> TimeSlot | None:
    """
    Return a portion of a free slot that fits inside the
    preferred scheduling window.

    Example:

        Free slot:
            14:00 -> 18:00

        Preferred:
            16:00 -> 18:00

        Result:
            16:00 -> 18:00

    Returns None when the preferred portion cannot provide
    the requested duration.
    """

    if preferred_window is None:
        return slot

    preferred_start = _parse_window_time(
        preferred_window.start_time,
    )

    preferred_end = _parse_window_time(
        preferred_window.end_time,
    )

    slot_start = slot.start
    slot_end = slot.end

    # ---------------------------------------------------------
    # NORMAL SAME-DAY WINDOW
    # ---------------------------------------------------------

    if preferred_start <= preferred_end:

        preferred_start_dt = slot_start.replace(
            hour=preferred_start.hour,
            minute=preferred_start.minute,
            second=0,
            microsecond=0,
        )

        preferred_end_dt = slot_start.replace(
            hour=preferred_end.hour,
            minute=preferred_end.minute,
            second=0,
            microsecond=0,
        )

        candidate_start = max(
            slot_start,
            preferred_start_dt,
        )

        candidate_end = min(
            slot_end,
            preferred_end_dt,
        )

        if candidate_end <= candidate_start:
            return None

        duration = int(
            (
                candidate_end
                - candidate_start
            ).total_seconds()
            // 60
        )

        if duration < required_minutes:
            return None

        return TimeSlot(
            start=candidate_start,
            end=candidate_end,
            duration_minutes=duration,
        )

    # ---------------------------------------------------------
    # OVERNIGHT WINDOW
    #
    # Example:
    #     22:00 -> 02:00
    # ---------------------------------------------------------

    evening_start = slot_start.replace(
        hour=preferred_start.hour,
        minute=preferred_start.minute,
        second=0,
        microsecond=0,
    )

    if slot_start.date() != slot_end.date():

        # Slot itself crosses midnight.
        evening_end = slot_end

    else:

        evening_end = slot_end

    candidate_start = max(
        slot_start,
        evening_start,
    )

    if candidate_start < evening_end:

        duration = int(
            (
                evening_end
                - candidate_start
            ).total_seconds()
            // 60
        )

        if duration >= required_minutes:
            return TimeSlot(
                start=candidate_start,
                end=evening_end,
                duration_minutes=duration,
            )

    # Morning portion on the next day.
    morning_end = slot_start.replace(
        hour=preferred_end.hour,
        minute=preferred_end.minute,
        second=0,
        microsecond=0,
    )

    if preferred_end < preferred_start:
        morning_end += timedelta(
            days=1,
        )

    candidate_start = slot_start
    candidate_end = min(
        slot_end,
        morning_end,
    )

    if candidate_end > candidate_start:

        duration = int(
            (
                candidate_end
                - candidate_start
            ).total_seconds()
            // 60
        )

        if duration >= required_minutes:
            return TimeSlot(
                start=candidate_start,
                end=candidate_end,
                duration_minutes=duration,
            )

    return None


def _sort_slots(
    slots: list[TimeSlot],
    task: Task,
) -> list[TimeSlot]:
    """
    Sort available slots deterministically.

    Preferred-window matches come first.
    Earlier slots win ties.
    """

    return sorted(
        slots,
        key=lambda slot: (
            0
            if _slot_matches_preference(
                slot,
                task.preferred_window,
            )
            else 1,
            slot.start,
            slot.end,
        ),
    )


def _make_block(
    task: Task,
    slot: TimeSlot,
    duration_minutes: int,
) -> ProposedBlock:
    """
    Create a proposed block.

    For a partial split, construct a new TimeSlot beginning
    at the available slot's start.
    """

    if duration_minutes == _slot_minutes(slot):
        selected_slot = slot

    else:
        end = slot.start + timedelta(
            minutes=duration_minutes,
        )

        selected_slot = TimeSlot(
            start=slot.start,
            end=end,
            duration_minutes=duration_minutes,
        )

    return ProposedBlock(
        task_title=task.title,
        slot=selected_slot,
    )


def schedule_task(
    task: Task,
    available_slots: list[TimeSlot],
) -> TaskScheduleProposal:
    """
    Propose a schedule for one task.

    Rules:

    - Never creates Google Calendar events.
    - Never modifies calendar data.
    - Respects the task deadline.
    - Respects the preferred scheduling window when possible.
    - Non-splittable tasks require one complete slot.
    - Splittable tasks may use multiple slots.
    - Capacity shortages are explicitly reported.
    """

    candidates = [
        slot
        for slot in available_slots
        if _slot_before_deadline(
            slot,
            task.deadline,
        )
    ]

    candidates = _sort_slots(
        candidates,
        task,
    )

    required = task.duration_minutes

    # ---------------------------------------------------------
    # PREFERRED WINDOW
    # ---------------------------------------------------------

    if task.preferred_window is not None:

        preferred_candidates: list[
            TimeSlot
        ] = []

        for candidate in candidates:

            preferred_candidate = (
                _preferred_candidate_slot(
                    candidate,
                    task.preferred_window,
                    required,
                )
            )

            if preferred_candidate is not None:
                preferred_candidates.append(
                    preferred_candidate
                )

        # Only replace the candidate list when at least
        # one slot can fully satisfy the task inside the
        # preferred window.
        if preferred_candidates:
            candidates = preferred_candidates

    # ---------------------------------------------------------
    # NON-SPLITTABLE TASK
    # ---------------------------------------------------------

    if not task.splittable:

        for slot in candidates:

            capacity = _slot_minutes(
                slot,
            )

            if capacity < required:
                continue

            block = _make_block(
                task,
                slot,
                required,
            )

            return TaskScheduleProposal(
                blocks=[block],
                unscheduled_minutes=0,
                status="fully_scheduled",
            )

        return TaskScheduleProposal(
            blocks=[],
            unscheduled_minutes=required,
            status="insufficient_capacity",
        )

    # ---------------------------------------------------------
    # SPLITTABLE TASK
    # ---------------------------------------------------------

    blocks: list[ProposedBlock] = []
    remaining = required

    for slot in candidates:

        if remaining <= 0:
            break

        capacity = _slot_minutes(
            slot,
        )

        if capacity <= 0:
            continue

        use_minutes = min(
            capacity,
            remaining,
        )

        blocks.append(
            _make_block(
                task,
                slot,
                use_minutes,
            )
        )

        remaining -= use_minutes

    if remaining == 0:
        status = "fully_scheduled"

    elif blocks:
        status = "partially_scheduled"

    else:
        status = "insufficient_capacity"

    return TaskScheduleProposal(
        blocks=blocks,
        unscheduled_minutes=remaining,
        status=status,
    )


def schedule_tasks(
    tasks: list[Task],
    available_slots: list[TimeSlot],
) -> dict[str, TaskScheduleProposal]:
    """
    Schedule multiple tasks against the same availability.

    Higher-priority tasks are considered first.

    Proposed blocks are removed from the remaining capacity so
    two tasks cannot receive the same block.

    No Google Calendar write operation is performed.
    """

    ordered_tasks = sorted(
        tasks,
        key=lambda task: (
            _PRIORITY_ORDER[
                task.priority
            ],
            task.deadline or date.max,
            task.title.lower(),
        ),
    )

    remaining_slots = list(
        available_slots,
    )

    results: dict[
        str,
        TaskScheduleProposal,
    ] = {}

    for task in ordered_tasks:

        proposal = schedule_task(
            task,
            remaining_slots,
        )

        results[task.title] = proposal

        remaining_slots = _remove_proposed_blocks(
            remaining_slots,
            proposal.blocks,
        )

    return results


def _remove_proposed_blocks(
    slots: list[TimeSlot],
    blocks: list[ProposedBlock],
) -> list[TimeSlot]:
    """
    Remove proposed blocks from available slots.

    Handles:

    - complete consumption
    - beginning consumption
    - ending consumption
    - middle splitting
    """

    remaining = list(slots)

    for block in blocks:

        block_start = block.slot.start
        block_end = block.slot.end

        updated: list[TimeSlot] = []

        for slot in remaining:

            slot_start = slot.start
            slot_end = slot.end

            # No overlap.
            if (
                block_end <= slot_start
                or block_start >= slot_end
            ):
                updated.append(slot)
                continue

            # Block consumes the whole slot.
            if (
                block_start <= slot_start
                and block_end >= slot_end
            ):
                continue

            # Keep left portion.
            if block_start > slot_start:

                left_minutes = int(
                    (
                        block_start
                        - slot_start
                    ).total_seconds()
                    // 60
                )

                if left_minutes > 0:

                    updated.append(
                        TimeSlot(
                            start=slot_start,
                            end=block_start,
                            duration_minutes=left_minutes,
                        )
                    )

            # Keep right portion.
            if block_end < slot_end:

                right_minutes = int(
                    (
                        slot_end
                        - block_end
                    ).total_seconds()
                    // 60
                )

                if right_minutes > 0:

                    updated.append(
                        TimeSlot(
                            start=block_end,
                            end=slot_end,
                            duration_minutes=right_minutes,
                        )
                    )

        remaining = updated

    return sorted(
        remaining,
        key=lambda slot: slot.start,
    )