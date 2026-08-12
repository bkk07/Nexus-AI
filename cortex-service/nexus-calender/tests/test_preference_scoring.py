from datetime import datetime
from zoneinfo import ZoneInfo

from best_slot import (
    score_window_preference,
    BestSlotService,
)
from models import TimeSlot


IST = ZoneInfo("Asia/Kolkata")


def make_slot(
    start_hour: int,
    end_hour: int,
) -> TimeSlot:

    start = datetime(
        2026,
        8,
        12,
        start_hour,
        tzinfo=IST,
    )

    end = datetime(
        2026,
        8,
        12,
        end_hour,
        tzinfo=IST,
    )

    return TimeSlot(
        start=start,
        end=end,
        duration_minutes=(
            end_hour - start_hour
        ) * 60,
    )


def test_slot_inside_preferred_window_scores_one():

    slot = make_slot(19, 20)

    score = score_window_preference(
        slot,
        preferred_window_start=(
            __import__("datetime").time(18, 0)
        ),
        preferred_window_end=(
            __import__("datetime").time(22, 0)
        ),
    )

    assert score == 1.0


def test_slot_outside_preferred_window_scores_zero():

    slot = make_slot(10, 11)

    score = score_window_preference(
        slot,
        preferred_window_start=(
            __import__("datetime").time(18, 0)
        ),
        preferred_window_end=(
            __import__("datetime").time(22, 0)
        ),
    )

    assert score == 0.0


def test_partial_overlap_gets_partial_score():

    slot = make_slot(17, 19)

    score = score_window_preference(
        slot,
        preferred_window_start=(
            __import__("datetime").time(18, 0)
        ),
        preferred_window_end=(
            __import__("datetime").time(22, 0)
        ),
    )

    assert score == 0.5


def test_no_preference_returns_one():

    slot = make_slot(10, 11)

    score = score_window_preference(
        slot,
    )

    assert score == 1.0


def test_preferred_window_changes_best_slot():

    service = BestSlotService()

    morning = make_slot(10, 11)
    evening = make_slot(19, 20)

    ranked = service.rank_slots(
        slots=[
            morning,
            evening,
        ],
        requested_duration_minutes=60,
        preferred_window_start=(
            __import__("datetime").time(18, 0)
        ),
        preferred_window_end=(
            __import__("datetime").time(22, 0)
        ),
    )

    assert ranked[0].slot == evening

    assert ranked[0].score > ranked[1].score