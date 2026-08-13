from __future__ import annotations

from datetime import date, timedelta, time
from typing import Iterable

from pydantic import BaseModel, Field

from models import RankedSlot, TimeSlot
from best_slot import BestSlotService


class HabitDefinition(BaseModel):
    """
    Definition of a recurring scheduling habit.

    The habit describes what should be scheduled and on which
    calendar days it applies.
    """

    title: str = Field(min_length=1)

    duration_minutes: int = Field(
        gt=0,
    )

    applies_weekdays: list[int] = Field(
        default_factory=lambda: [
            0,
            1,
            2,
            3,
            4,
        ],
    )

    preferred_window_start: time | None = None

    preferred_window_end: time | None = None

    start_date: date

    end_date: date


class HabitDayProposal(BaseModel):
    """
    Scheduling result for one applicable day.

    Every applicable day gets a result, even when no
    suitable slot exists.
    """

    date: date

    scheduled: bool

    slot: TimeSlot | None = None

    score: float | None = None

    reasons: list[str] = Field(
        default_factory=list,
    )


class HabitProposal(BaseModel):
    """
    Complete recurring-habit scheduling proposal.
    """

    habit: HabitDefinition

    days: list[HabitDayProposal] = Field(
        default_factory=list,
    )

    scheduled_days: int

    unscheduled_days: int

    total_applicable_days: int

    summary: str


def _validate_weekdays(
    weekdays: Iterable[int],
) -> list[int]:

    normalized = list(
        dict.fromkeys(weekdays)
    )

    for weekday in normalized:
        if weekday < 0 or weekday > 6:
            raise ValueError(
                "Weekdays must be between 0 and 6."
            )

    return normalized


def _dates_in_range(
    start_date: date,
    end_date: date,
):
    if end_date < start_date:
        raise ValueError(
            "end_date must be on or after start_date."
        )

    current = start_date

    while current <= end_date:
        yield current
        current += timedelta(days=1)


def _slots_for_date(
    slots: list[TimeSlot],
    target_date: date,
) -> list[TimeSlot]:

    return [
        slot
        for slot in slots
        if slot.start.date() == target_date
    ]


def propose_habit_schedule(
    habit: HabitDefinition,
    available_slots_by_date: dict[
        date,
        list[TimeSlot],
    ],
    *,
    best_slot_service: BestSlotService | None = None,
) -> HabitProposal:
    """
    Propose recurring scheduling for a habit.

    Phase 22 deliberately delegates slot selection to the
    existing BestSlotService.

    No new ranking or interval-selection algorithm is
    introduced here.

    Every applicable day is represented in the result.
    """

    weekdays = _validate_weekdays(
        habit.applies_weekdays,
    )

    service = (
        best_slot_service
        if best_slot_service is not None
        else BestSlotService()
    )

    day_results: list[HabitDayProposal] = []

    for current_date in _dates_in_range(
        habit.start_date,
        habit.end_date,
    ):

        # Non-applicable weekday.
        if current_date.weekday() not in weekdays:
            continue

        day_slots = _slots_for_date(
            available_slots_by_date.get(
                current_date,
                [],
            ),
            current_date,
        )

        best = service.find_best_slot(
            slots=day_slots,
            requested_duration_minutes=(
                habit.duration_minutes
            ),
            preferred_window_start=(
                habit.preferred_window_start
            ),
            preferred_window_end=(
                habit.preferred_window_end
            ),
        )

        if best is None:

            day_results.append(
                HabitDayProposal(
                    date=current_date,
                    scheduled=False,
                    slot=None,
                    score=None,
                    reasons=[
                        "no viable slot",
                    ],
                )
            )

            continue

        day_results.append(
            HabitDayProposal(
                date=current_date,
                scheduled=True,
                slot=best.slot,
                score=best.score,
                reasons=list(
                    best.reasons
                ),
            )
        )

    scheduled_days = sum(
        1
        for result in day_results
        if result.scheduled
    )

    total_applicable_days = len(
        day_results
    )

    unscheduled_days = (
        total_applicable_days
        - scheduled_days
    )

    if unscheduled_days == 0:

        summary = (
            f"{scheduled_days} of "
            f"{total_applicable_days} days "
            "scheduled successfully."
        )

    else:

        summary = (
            f"{unscheduled_days} of "
            f"{total_applicable_days} days "
            "could not be scheduled."
        )

    return HabitProposal(
        habit=habit,
        days=day_results,
        scheduled_days=scheduled_days,
        unscheduled_days=unscheduled_days,
        total_applicable_days=(
            total_applicable_days
        ),
        summary=summary,
    )