from __future__ import annotations

from datetime import datetime, time

from models import RankedSlot, TimeSlot


# =========================================================
# PHASE 10 SCORING WEIGHTS
# =========================================================

SCORE_WEIGHTS = {
    "time_preference": 0.30,
    "duration_fit": 0.25,
    "block_length": 0.20,
    "event_distance": 0.15,
    "fragmentation": 0.10,
}


def _clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:

    return max(
        minimum,
        min(maximum, value),
    )


# =========================================================
# PHASE 10 - TIME PREFERENCE
# =========================================================

def score_time_preference(
    slot: TimeSlot,
    *,
    preferred_start: time | None = None,
    preferred_window_start: time | None = None,
    preferred_window_end: time | None = None,
) -> float:
    """
    Score how well a slot matches the user's time preference.

    Priority:

        1. Preferred scheduling window
        2. Explicit preferred start time
        3. No preference -> 1.0

    Phase 18 adds preferred-window support while
    preserving the original Phase 10 behavior.
    """

    # -----------------------------------------------------
    # Phase 18 - Preferred Window
    # -----------------------------------------------------

    if (
        preferred_window_start is not None
        or preferred_window_end is not None
    ):

        return score_window_preference(
            slot,
            preferred_window_start=(
                preferred_window_start
            ),
            preferred_window_end=(
                preferred_window_end
            ),
        )

    # -----------------------------------------------------
    # Existing Phase 10 behavior
    # -----------------------------------------------------

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


# =========================================================
# PHASE 18 - PREFERRED WINDOW SCORE
# =========================================================

def score_window_preference(
    slot: TimeSlot,
    *,
    preferred_window_start: time | None = None,
    preferred_window_end: time | None = None,
) -> float:
    """
    Score how well a candidate slot fits a preferred
    scheduling window.

    Score:

        1.0 -> slot completely inside preferred window
        0.0 -> slot completely outside preferred window
        partial overlap -> proportional score

    If no preferred window is supplied, return 1.0.
    """

    # No preference.
    if (
        preferred_window_start is None
        and preferred_window_end is None
    ):
        return 1.0

    # Only one boundary supplied.
    if (
        preferred_window_start is None
        or preferred_window_end is None
    ):
        raise ValueError(
            "Both preferred_window_start and "
            "preferred_window_end must be provided."
        )

    preferred_start_minutes = (
        preferred_window_start.hour * 60
        + preferred_window_start.minute
    )

    preferred_end_minutes = (
        preferred_window_end.hour * 60
        + preferred_window_end.minute
    )

    if preferred_end_minutes <= preferred_start_minutes:
        raise ValueError(
            "Preferred window end must be after start."
        )

    slot_start_minutes = (
        slot.start.hour * 60
        + slot.start.minute
    )

    slot_end_minutes = (
        slot.end.hour * 60
        + slot.end.minute
    )

    if slot_end_minutes <= slot_start_minutes:
        return 0.0

    overlap_start = max(
        slot_start_minutes,
        preferred_start_minutes,
    )

    overlap_end = min(
        slot_end_minutes,
        preferred_end_minutes,
    )

    overlap = max(
        0,
        overlap_end - overlap_start,
    )

    slot_duration = (
        slot_end_minutes
        - slot_start_minutes
    )

    return _clamp(
        overlap / slot_duration
    )


# =========================================================
# PHASE 10 - DURATION FIT
# =========================================================

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
        1.0
        + extra / requested_duration_minutes
    )


# =========================================================
# PHASE 10 - BLOCK LENGTH
# =========================================================

def score_block_length(
    slot: TimeSlot,
    *,
    max_block_minutes: int | None = None,
) -> float:
    """
    Score the amount of uninterrupted free time.

    If max_block_minutes is supplied, use it as the
    normalization boundary.

    Otherwise 8 hours is used as a practical upper bound.
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


# =========================================================
# PHASE 10 - EVENT DISTANCE
# =========================================================

def score_event_distance(
    slot: TimeSlot,
    *,
    previous_busy_end: datetime | None = None,
    next_busy_start: datetime | None = None,
    buffer_minutes: int = 0,
) -> float:
    """
    Score breathing room around the candidate slot.

    The optional buffer parameter is intentionally accepted
    so Phase 16 can reuse this scorer.
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
            ).total_seconds()
            / 60
        )

    if next_busy_start is not None:

        distances.append(
            (
                next_busy_start
                - slot.end
            ).total_seconds()
            / 60
        )

    if not distances:
        return 1.0

    minimum_distance = max(
        0.0,
        min(distances) - buffer_minutes,
    )

    # 2 hours of breathing room is treated
    # as the maximum useful value.
    return _clamp(
        minimum_distance / 120
    )


# =========================================================
# PHASE 10 - FRAGMENTATION
# =========================================================

def score_fragmentation(
    slot: TimeSlot,
    *,
    minimum_useful_gap_minutes: int = 30,
) -> float:
    """
    Basic fragmentation score.

    Larger candidate slots are preferred because they are
    less likely to leave an unusable scheduling gap.

    This is deterministic and self-contained.
    """

    if minimum_useful_gap_minutes <= 0:
        raise ValueError(
            "minimum_useful_gap_minutes must be positive."
        )

    if (
        slot.duration_minutes
        < minimum_useful_gap_minutes
    ):
        return 0.0

    return 1.0


# =========================================================
# BEST SLOT SERVICE
# =========================================================

class BestSlotService:
    """
    Deterministically ranks free TimeSlot candidates.

    No Groq calls.
    No Google API calls.
    No natural-language interpretation.

    Phase 18:
        User preferred scheduling windows can influence
        the time-preference score.
    """

    def rank_slots(
        self,
        *,
        slots: list[TimeSlot],
        requested_duration_minutes: int,
        preferred_start: time | None = None,
        preferred_window_start: time | None = None,
        preferred_window_end: time | None = None,
        previous_busy_ends: dict[
            datetime,
            datetime,
        ] | None = None,
        next_busy_starts: dict[
            datetime,
            datetime,
        ] | None = None,
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

            # -------------------------------------------------
            # Time preference
            # -------------------------------------------------

            time_score = score_time_preference(
                slot,
                preferred_start=preferred_start,
                preferred_window_start=(
                    preferred_window_start
                ),
                preferred_window_end=(
                    preferred_window_end
                ),
            )

            # -------------------------------------------------
            # Duration fit
            # -------------------------------------------------

            duration_score = score_duration_fit(
                slot,
                requested_duration_minutes=(
                    requested_duration_minutes
                ),
            )

            # -------------------------------------------------
            # Block length
            # -------------------------------------------------

            block_score = score_block_length(
                slot,
            )

            # -------------------------------------------------
            # Event distance
            # -------------------------------------------------

            previous_end = None
            next_start = None

            if previous_busy_ends:

                previous_end = (
                    previous_busy_ends.get(
                        slot.start
                    )
                )

            if next_busy_starts:

                next_start = (
                    next_busy_starts.get(
                        slot.start
                    )
                )

            distance_score = score_event_distance(
                slot,
                previous_busy_end=previous_end,
                next_busy_start=next_start,
                buffer_minutes=buffer_minutes,
            )

            # -------------------------------------------------
            # Fragmentation
            # -------------------------------------------------

            fragmentation_score = (
                score_fragmentation(
                    slot,
                )
            )

            # -------------------------------------------------
            # Total deterministic score
            # -------------------------------------------------

            total_score = (
                SCORE_WEIGHTS[
                    "time_preference"
                ]
                * time_score

                + SCORE_WEIGHTS[
                    "duration_fit"
                ]
                * duration_score

                + SCORE_WEIGHTS[
                    "block_length"
                ]
                * block_score

                + SCORE_WEIGHTS[
                    "event_distance"
                ]
                * distance_score

                + SCORE_WEIGHTS[
                    "fragmentation"
                ]
                * fragmentation_score
            )

            # -------------------------------------------------
            # Reasons
            # -------------------------------------------------

            reasons: list[str] = []

            if (
                preferred_start is not None
                or preferred_window_start is not None
                or preferred_window_end is not None
            ):
                reasons.append(
                    f"time preference score="
                    f"{time_score:.3f}"
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
                "uninterrupted block="
                f"{slot.duration_minutes} minutes"
            )

            reasons.append(
                "event-distance score="
                f"{distance_score:.3f}"
            )

            reasons.append(
                "fragmentation score="
                f"{fragmentation_score:.3f}"
            )

            # -------------------------------------------------
            # Ranked result
            # -------------------------------------------------

            ranked.append(
                RankedSlot(
                    slot=slot,
                    score=total_score,
                    reasons=reasons,
                )
            )

        # Highest score first.
        # Earlier slot wins ties.
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
        preferred_window_start: time | None = None,
        preferred_window_end: time | None = None,
        previous_busy_ends: dict[
            datetime,
            datetime,
        ] | None = None,
        next_busy_starts: dict[
            datetime,
            datetime,
        ] | None = None,
        buffer_minutes: int = 0,
    ) -> RankedSlot | None:
        """
        Return the highest-ranked valid slot.

        Returns None when no candidate satisfies
        the requested duration.
        """

        ranked = self.rank_slots(
            slots=slots,
            requested_duration_minutes=(
                requested_duration_minutes
            ),
            preferred_start=preferred_start,
            preferred_window_start=(
                preferred_window_start
            ),
            preferred_window_end=(
                preferred_window_end
            ),
            previous_busy_ends=previous_busy_ends,
            next_busy_starts=next_busy_starts,
            buffer_minutes=buffer_minutes,
        )

        if not ranked:
            return None

        return ranked[0]