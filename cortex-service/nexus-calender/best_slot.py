from __future__ import annotations

from datetime import datetime, time

from models import RankedSlot, TimeSlot


# Phase 10 scoring weights.
#
# Keep all weights in one place so the ranking policy
# can be changed without modifying individual scorers.
SCORE_WEIGHTS = {
    "time_preference": 0.30,
    "duration_fit": 0.25,
    "block_length": 0.20,
    "event_distance": 0.15,
    "fragmentation": 0.10,
}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def score_time_preference(
    slot: TimeSlot,
    *,
    preferred_start: time | None = None,
) -> float:
    """
    Score how close the slot is to the requested time preference.

    If no preference is supplied, every slot receives the same score.
    """

    if preferred_start is None:
        return 1.0

    slot_minutes = (
        slot.start.hour * 60
        + slot.start.minute
    )

    preferred_minutes = (
        preferred_start.hour * 60
        + preferred_start.minute
    )

    distance = abs(
        slot_minutes - preferred_minutes
    )

    # Maximum useful distance = 12 hours.
    return _clamp(
        1.0 - distance / (12 * 60)
    )


def score_duration_fit(
    slot: TimeSlot,
    *,
    requested_duration_minutes: int,
) -> float:
    """
    Prefer slots that are close to the requested duration.

    A slot must already satisfy the requested duration.
    """

    if requested_duration_minutes <= 0:
        raise ValueError(
            "requested_duration_minutes must be positive."
        )

    if slot.duration_minutes < requested_duration_minutes:
        return 0.0

    extra = (
        slot.duration_minutes
        - requested_duration_minutes
    )

    # Exact match = 1.0.
    # Larger free blocks gradually receive a lower score.
    return 1.0 / (
        1.0 + extra / requested_duration_minutes
    )


def score_block_length(
    slot: TimeSlot,
    *,
    max_block_minutes: int | None = None,
) -> float:
    """
    Score the amount of uninterrupted free time.

    If max_block_minutes is supplied, use it as the normalization
    boundary. Otherwise 8 hours is used as a practical upper bound.
    """

    maximum = (
        max_block_minutes
        if max_block_minutes is not None
        else 8 * 60
    )

    if maximum <= 0:
        raise ValueError(
            "max_block_minutes must be positive."
        )

    return _clamp(
        slot.duration_minutes / maximum
    )


def score_event_distance(
    slot: TimeSlot,
    *,
    previous_busy_end: datetime | None = None,
    next_busy_start: datetime | None = None,
    buffer_minutes: int = 0,
) -> float:
    """
    Score breathing room around the candidate slot.

    The optional buffer parameter is intentionally accepted now
    so Phase 16 can reuse this scorer later.
    """

    if buffer_minutes < 0:
        raise ValueError(
            "buffer_minutes cannot be negative."
        )

    distances: list[float] = []

    if previous_busy_end is not None:
        distances.append(
            (
                slot.start
                - previous_busy_end
            ).total_seconds() / 60
        )

    if next_busy_start is not None:
        distances.append(
            (
                next_busy_start
                - slot.end
            ).total_seconds() / 60
        )

    if not distances:
        return 1.0

    minimum_distance = max(
        0.0,
        min(distances) - buffer_minutes,
    )

    # 2 hours of breathing room is treated as the
    # maximum useful value.
    return _clamp(
        minimum_distance / 120
    )


def score_fragmentation(
    slot: TimeSlot,
    *,
    minimum_useful_gap_minutes: int = 30,
) -> float:
    """
    Basic fragmentation score.

    Larger candidate slots are preferred because they are
    less likely to leave an unusable scheduling gap.

    This is deliberately deterministic and self-contained.
    """

    if minimum_useful_gap_minutes <= 0:
        raise ValueError(
            "minimum_useful_gap_minutes must be positive."
        )

    if slot.duration_minutes < minimum_useful_gap_minutes:
        return 0.0

    return 1.0


class BestSlotService:
    """
    Deterministically ranks free TimeSlot candidates.

    No Groq calls.
    No Google API calls.
    No natural-language interpretation.
    """

    def rank_slots(
        self,
        *,
        slots: list[TimeSlot],
        requested_duration_minutes: int,
        preferred_start: time | None = None,
        previous_busy_ends: dict[datetime, datetime] | None = None,
        next_busy_starts: dict[datetime, datetime] | None = None,
        buffer_minutes: int = 0,
    ) -> list[RankedSlot]:
        """
        Rank all valid candidate slots.

        Candidates are returned in descending score order.
        Ties are resolved by earlier start time.
        """

        if requested_duration_minutes <= 0:
            raise ValueError(
                "requested_duration_minutes must be positive."
            )

        valid_slots = [
            slot
            for slot in slots
            if slot.duration_minutes
            >= requested_duration_minutes
        ]

        ranked: list[RankedSlot] = []

        for slot in valid_slots:

            time_score = score_time_preference(
                slot,
                preferred_start=preferred_start,
            )

            duration_score = score_duration_fit(
                slot,
                requested_duration_minutes=(
                    requested_duration_minutes
                ),
            )

            block_score = score_block_length(
                slot,
            )

            previous_end = None
            next_start = None

            if previous_busy_ends:
                previous_end = previous_busy_ends.get(
                    slot.start
                )

            if next_busy_starts:
                next_start = next_busy_starts.get(
                    slot.start
                )

            distance_score = score_event_distance(
                slot,
                previous_busy_end=previous_end,
                next_busy_start=next_start,
                buffer_minutes=buffer_minutes,
            )

            fragmentation_score = score_fragmentation(
                slot,
            )

            total_score = (
                SCORE_WEIGHTS["time_preference"]
                * time_score
                + SCORE_WEIGHTS["duration_fit"]
                * duration_score
                + SCORE_WEIGHTS["block_length"]
                * block_score
                + SCORE_WEIGHTS["event_distance"]
                * distance_score
                + SCORE_WEIGHTS["fragmentation"]
                * fragmentation_score
            )

            reasons: list[str] = []

            if preferred_start is not None:
                reasons.append(
                    f"time preference score={time_score:.3f}"
                )

            if duration_score == 1.0:
                reasons.append(
                    "exact duration fit"
                )
            else:
                reasons.append(
                    "longer than requested"
                )

            reasons.append(
                f"uninterrupted block={slot.duration_minutes} minutes"
            )

            reasons.append(
                f"event-distance score={distance_score:.3f}"
            )

            reasons.append(
                f"fragmentation score={fragmentation_score:.3f}"
            )

            ranked.append(
                RankedSlot(
                    slot=slot,
                    score=total_score,
                    reasons=reasons,
                )
            )

        ranked.sort(
            key=lambda item: (
                -item.score,
                item.slot.start,
            )
        )

        return ranked

    def find_best_slot(
        self,
        *,
        slots: list[TimeSlot],
        requested_duration_minutes: int,
        preferred_start: time | None = None,
        previous_busy_ends: dict[datetime, datetime] | None = None,
        next_busy_starts: dict[datetime, datetime] | None = None,
        buffer_minutes: int = 0,
    ) -> RankedSlot | None:
        """
        Return the highest-ranked valid slot.

        Returns None when no candidate satisfies the duration.
        """

        ranked = self.rank_slots(
            slots=slots,
            requested_duration_minutes=(
                requested_duration_minutes
            ),
            preferred_start=preferred_start,
            previous_busy_ends=previous_busy_ends,
            next_busy_starts=next_busy_starts,
            buffer_minutes=buffer_minutes,
        )

        if not ranked:
            return None

        return ranked[0]