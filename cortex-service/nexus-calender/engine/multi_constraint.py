from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Literal

from pydantic import BaseModel, Field

from datetime_utils import DateTimeRange
from models import (
    CalendarMultiConstraintRequest,
    RankedSlot,
    TimeSlot,
)
from free_slots import find_free_slots
from best_slot import BestSlotService


class MultiConstraintResult(BaseModel):
    """
    Result of multi-constraint scheduling.

    The engine separates:
        - hard constraints
        - soft preferences
        - optional multi-block requirements
    """

    status: Literal[
        "feasible",
        "infeasible",
    ]

    blocks: list[TimeSlot] = Field(
        default_factory=list,
    )

    ranked_slots: list[RankedSlot] = Field(
        default_factory=list,
    )

    unscheduled_minutes: int = 0

    explanation: list[str] = Field(
        default_factory=list,
    )


def _parse_time(
    value: str | time | None,
) -> time | None:

    if value is None:
        return None

    if isinstance(value, time):
        return value

    return time.fromisoformat(value)


def _build_window(
    base_window: DateTimeRange,
    request: CalendarMultiConstraintRequest,
) -> DateTimeRange:
    """
    Apply HARD time-window constraints.

    Example:

        base window: 09:00 -> 22:00
        hard end:    21:00

    becomes:

        09:00 -> 21:00
    """

    start = base_window.start
    end = base_window.end

    hard_start = _parse_time(
        request.hard_start_time,
    )

    hard_end = _parse_time(
        request.hard_end_time,
    )

    if hard_start is not None:

        candidate = start.replace(
            hour=hard_start.hour,
            minute=hard_start.minute,
            second=0,
            microsecond=0,
        )

        if candidate > start:
            start = candidate

    if hard_end is not None:

        candidate = end.replace(
            hour=hard_end.hour,
            minute=hard_end.minute,
            second=0,
            microsecond=0,
        )

        if candidate < end:
            end = candidate

    if end <= start:

        raise ValueError(
            "Hard scheduling constraints leave "
            "an invalid scheduling window."
        )

    return DateTimeRange(
        start=start,
        end=end,
    )


def _apply_deadline(
    window: DateTimeRange,
    deadline: datetime | None,
) -> DateTimeRange:

    if deadline is None:
        return window

    end = min(
        window.end,
        deadline,
    )

    if end <= window.start:

        raise ValueError(
            "Deadline leaves no valid scheduling window."
        )

    return DateTimeRange(
        start=window.start,
        end=end,
    )


def _rank_with_preferences(
    slots: list[TimeSlot],
    request: CalendarMultiConstraintRequest,
) -> list[RankedSlot]:
    """
    Delegate ranking to the existing Phase 10 engine.

    Phase 24 does not implement a new ranking algorithm.
    """

    preferred_start = _parse_time(
        request.preferred_start_time,
    )

    preferred_end = _parse_time(
        request.preferred_end_time,
    )

    service = BestSlotService()

    return service.rank_slots(
        slots=slots,
        requested_duration_minutes=(
            request.duration_minutes
        ),
        preferred_window_start=preferred_start,
        preferred_window_end=preferred_end,
    )


def _trim_slot(
    slot: TimeSlot,
    duration_minutes: int,
) -> TimeSlot:
    """
    Trim a qualifying free slot to exactly the
    duration requested by the user.

    The original free slot remains available as the
    Phase 8 candidate, but the proposed scheduling
    block represents only the requested duration.
    """

    if duration_minutes <= 0:
        raise ValueError(
            "duration_minutes must be positive."
        )

    if slot.duration_minutes < duration_minutes:
        raise ValueError(
            "Slot is shorter than requested duration."
        )

    end = slot.start + timedelta(
        minutes=duration_minutes,
    )

    return TimeSlot(
        start=slot.start,
        end=end,
        duration_minutes=duration_minutes,
    )

def _select_two_blocks(
    slots: list[TimeSlot],
    duration_minutes: int,
) -> list[TimeSlot] | None:
    """
    Select exactly two uninterrupted slots whose combined
    duration is exactly the requested duration.

    Both blocks must contribute a positive amount of time.

    The source slots are produced by Phase 8, so this function
    does not perform new interval/free-slot calculations.
    """

    if duration_minutes <= 0:
        raise ValueError(
            "duration_minutes must be positive."
        )

    if len(slots) < 2:
        return None

    for first_index in range(len(slots)):

        first = slots[first_index]

        for second_index in range(
            first_index + 1,
            len(slots),
        ):

            second = slots[second_index]

            total = (
                first.duration_minutes
                + second.duration_minutes
            )

            if total < duration_minutes:
                continue

            # -------------------------------------------------
            # Try to distribute the requested duration between
            # BOTH blocks.
            #
            # Both portions must be > 0 because the request
            # explicitly asks for two blocks.
            # -------------------------------------------------

            first_minutes = min(
                first.duration_minutes,
                duration_minutes - 1,
            )

            remaining = (
                duration_minutes
                - first_minutes
            )

            second_minutes = min(
                second.duration_minutes,
                remaining,
            )

            if first_minutes <= 0:
                continue

            if second_minutes <= 0:
                continue

            if (
                first_minutes
                + second_minutes
                != duration_minutes
            ):
                continue

            first_block = TimeSlot(
                start=first.start,
                end=(
                    first.start
                    + timedelta(
                        minutes=first_minutes,
                    )
                ),
                duration_minutes=first_minutes,
            )

            second_block = TimeSlot(
                start=second.start,
                end=(
                    second.start
                    + timedelta(
                        minutes=second_minutes,
                    )
                ),
                duration_minutes=second_minutes,
            )

            return [
                first_block,
                second_block,
            ]

    return None


def find_multi_constraint_slots(
    request: CalendarMultiConstraintRequest,
    *,
    window: DateTimeRange,
    busy_intervals,
) -> MultiConstraintResult:
    """
    Main Phase 24 composition entry point.

    Composition:

        Phase 8
            ↓
        free slots

        Phase 17-style hard constraints
            ↓
        constrained window

        Phase 10
            ↓
        soft preference ranking

        Phase 20-style splitting
            ↓
        optional multiple blocks

    This function never writes to Google Calendar.
    """

    explanation: list[str] = []

    # =========================================================
    # 1. HARD CONSTRAINTS
    # =========================================================

    try:

        constrained_window = _build_window(
            window,
            request,
        )

        constrained_window = _apply_deadline(
            constrained_window,
            request.deadline,
        )

    except ValueError as exc:

        return MultiConstraintResult(
            status="infeasible",
            unscheduled_minutes=(
                request.duration_minutes
            ),
            explanation=[
                str(exc),
            ],
        )

    explanation.append(
        "Hard constraints applied."
    )

    # =========================================================
    # 2. PHASE 8 — FREE SLOTS
    # =========================================================

    free_slots = find_free_slots(
        window=constrained_window,
        busy_intervals=busy_intervals,
        minimum_duration_minutes=1,
    )

    if not free_slots:

        return MultiConstraintResult(
            status="infeasible",
            unscheduled_minutes=(
                request.duration_minutes
            ),
            explanation=[
                "Hard constraints leave no free slots."
            ],
        )

    explanation.append(
        "Phase 8 free-slot calculation reused."
    )

    # =========================================================
    # 3. SINGLE-BLOCK REQUEST
    # =========================================================

    if not request.split_required:

        qualifying = [
            slot
            for slot in free_slots
            if (
                slot.duration_minutes
                >= request.duration_minutes
            )
        ]

        if not qualifying:

            return MultiConstraintResult(
                status="infeasible",
                unscheduled_minutes=(
                    request.duration_minutes
                ),
                explanation=[
                    "No uninterrupted free slot "
                    "can satisfy the requested duration."
                ],
            )

        # -----------------------------------------------------
        # PHASE 10 — SOFT PREFERENCE RANKING
        # -----------------------------------------------------

        ranked = _rank_with_preferences(
            qualifying,
            request,
        )

        explanation.append(
            "Phase 10 soft-preference ranking reused."
        )

        # IMPORTANT:
        # BestSlotService ranks the complete free interval.
        # The actual proposed block must represent exactly
        # the duration requested by the user.
        selected_block = _trim_slot(
            ranked[0].slot,
            request.duration_minutes,
        )

        return MultiConstraintResult(
            status="feasible",
            blocks=[
                selected_block,
            ],
            ranked_slots=ranked,
            unscheduled_minutes=0,
            explanation=explanation,
        )

    # =========================================================
    # 4. MULTI-BLOCK REQUEST
    # =========================================================

    if request.number_of_blocks != 2:

        return MultiConstraintResult(
            status="infeasible",
            unscheduled_minutes=(
                request.duration_minutes
            ),
            explanation=[
                "Currently only exactly two-block "
                "scheduling is supported."
            ],
        )

    blocks = _select_two_blocks(
        free_slots,
        request.duration_minutes,
    )

    if blocks is None:

        return MultiConstraintResult(
            status="infeasible",
            unscheduled_minutes=(
                request.duration_minutes
            ),
            explanation=[
                "Available free slots cannot provide "
                "the requested duration in exactly "
                "two uninterrupted blocks."
            ],
        )

    explanation.append(
        "Two-block scheduling composed from "
        "Phase 20-style task splitting."
    )

    # =========================================================
    # 5. PHASE 10 RANKING
    # =========================================================

    ranked = _rank_with_preferences(
        free_slots,
        request,
    )

    explanation.append(
        "Phase 10 soft-preference ranking reused."
    )

    return MultiConstraintResult(
        status="feasible",
        blocks=blocks,
        ranked_slots=ranked,
        unscheduled_minutes=0,
        explanation=explanation,
    )