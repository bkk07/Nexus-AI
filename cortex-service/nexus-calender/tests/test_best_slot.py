from datetime import datetime, time
from zoneinfo import ZoneInfo

from best_slot import (
    BestSlotService,
    SCORE_WEIGHTS,
    score_block_length,
    score_duration_fit,
    score_event_distance,
    score_fragmentation,
    score_time_preference,
)
from models import TimeSlot


IST = ZoneInfo("Asia/Kolkata")


def dt(
    day: int,
    hour: int,
    minute: int = 0,
) -> datetime:
    return datetime(
        2026,
        8,
        day,
        hour,
        minute,
        tzinfo=IST,
    )


def slot(
    day: int,
    start_hour: int,
    end_hour: int,
    start_minute: int = 0,
    end_minute: int = 0,
) -> TimeSlot:

    start = dt(
        day,
        start_hour,
        start_minute,
    )

    end = dt(
        day,
        end_hour,
        end_minute,
    )

    duration = int(
        (end - start).total_seconds() / 60
    )

    return TimeSlot(
        start=start,
        end=end,
        duration_minutes=duration,
    )


# ============================================================
# INDIVIDUAL SCORING COMPONENTS
# ============================================================


def test_time_preference_prefers_closer_slot():

    morning = slot(
        12,
        9,
        11,
    )

    evening = slot(
        12,
        18,
        20,
    )

    morning_score = score_time_preference(
        morning,
        preferred_start=time(9, 0),
    )

    evening_score = score_time_preference(
        evening,
        preferred_start=time(9, 0),
    )

    assert morning_score > evening_score


def test_exact_duration_gets_best_duration_score():

    exact = slot(
        12,
        10,
        12,
    )

    larger = slot(
        12,
        10,
        15,
    )

    exact_score = score_duration_fit(
        exact,
        requested_duration_minutes=120,
    )

    larger_score = score_duration_fit(
        larger,
        requested_duration_minutes=120,
    )

    assert exact_score == 1.0
    assert exact_score > larger_score


def test_longer_block_gets_higher_block_score():

    short = slot(
        12,
        10,
        11,
    )

    long = slot(
        12,
        10,
        14,
    )

    short_score = score_block_length(
        short,
    )

    long_score = score_block_length(
        long,
    )

    assert long_score > short_score


def test_more_event_distance_gets_higher_score():

    slot_a = slot(
        12,
        10,
        12,
    )

    slot_b = slot(
        12,
        14,
        16,
    )

    close_score = score_event_distance(
        slot_a,
        previous_busy_end=dt(12, 9, 30),
        next_busy_start=dt(12, 12, 30),
    )

    far_score = score_event_distance(
        slot_b,
        previous_busy_end=dt(12, 12),
        next_busy_start=dt(12, 18),
    )

    assert far_score > close_score


def test_fragmentation_score_is_deterministic():

    candidate = slot(
        12,
        10,
        12,
    )

    score1 = score_fragmentation(
        candidate,
    )

    score2 = score_fragmentation(
        candidate,
    )

    assert score1 == score2


# ============================================================
# RANKING
# ============================================================


def test_best_slot_is_deterministic():

    service = BestSlotService()

    candidates = [
        slot(12, 9, 11),
        slot(12, 14, 16),
        slot(12, 18, 20),
    ]

    result1 = service.find_best_slot(
        slots=candidates,
        requested_duration_minutes=120,
    )

    result2 = service.find_best_slot(
        slots=candidates,
        requested_duration_minutes=120,
    )

    assert result1 is not None
    assert result2 is not None

    assert result1.slot.start == result2.slot.start
    assert result1.slot.end == result2.slot.end
    assert result1.score == result2.score


def test_earlier_start_wins_tie():

    service = BestSlotService()

    candidates = [
        slot(12, 14, 16),
        slot(12, 10, 12),
    ]

    ranked = service.rank_slots(
        slots=candidates,
        requested_duration_minutes=120,
    )

    assert len(ranked) == 2

    assert ranked[0].slot.start == dt(
        12,
        10,
    )

    assert ranked[1].slot.start == dt(
        12,
        14,
    )


def test_evening_preference_ranks_evening_slot_higher():

    service = BestSlotService()

    morning = slot(
        12,
        9,
        11,
    )

    evening = slot(
        12,
        18,
        20,
    )

    ranked = service.rank_slots(
        slots=[
            morning,
            evening,
        ],
        requested_duration_minutes=120,
        preferred_start=time(18, 0),
    )

    assert ranked[0].slot.start == dt(
        12,
        18,
    )


def test_exact_duration_is_preferred_when_other_factors_equal():

    service = BestSlotService()

    exact = slot(
        12,
        10,
        12,
    )

    oversized = slot(
        12,
        14,
        18,
    )

    ranked = service.rank_slots(
        slots=[
            oversized,
            exact,
        ],
        requested_duration_minutes=120,
    )

    assert ranked[0].slot.start == dt(
        12,
        10,
    )


def test_reasons_are_populated():

    service = BestSlotService()

    candidate = slot(
        12,
        18,
        20,
    )

    result = service.find_best_slot(
        slots=[candidate],
        requested_duration_minutes=120,
        preferred_start=time(18, 0),
    )

    assert result is not None

    assert len(result.reasons) > 0

    assert all(
        isinstance(reason, str)
        for reason in result.reasons
    )


def test_single_candidate_still_runs_scorer():

    service = BestSlotService()

    candidate = slot(
        12,
        18,
        20,
    )

    result = service.find_best_slot(
        slots=[candidate],
        requested_duration_minutes=120,
    )

    assert result is not None
    assert result.slot == candidate
    assert result.score > 0
    assert result.reasons


def test_zero_candidates_returns_none():

    service = BestSlotService()

    result = service.find_best_slot(
        slots=[],
        requested_duration_minutes=120,
    )

    assert result is None


def test_candidates_shorter_than_requested_are_ignored():

    service = BestSlotService()

    short = slot(
        12,
        9,
        10,
    )

    valid = slot(
        12,
        12,
        14,
    )

    result = service.find_best_slot(
        slots=[
            short,
            valid,
        ],
        requested_duration_minutes=120,
    )

    assert result is not None

    assert result.slot == valid


def test_all_candidates_too_short_returns_none():

    service = BestSlotService()

    candidates = [
        slot(12, 9, 10),
        slot(12, 12, 13),
        slot(12, 15, 16),
    ]

    result = service.find_best_slot(
        slots=candidates,
        requested_duration_minutes=120,
    )

    assert result is None


# ============================================================
# WEIGHT CONFIGURATION
# ============================================================


def test_score_weights_are_defined_in_one_place():

    assert set(SCORE_WEIGHTS.keys()) == {
        "time_preference",
        "duration_fit",
        "block_length",
        "event_distance",
        "fragmentation",
    }

    assert abs(
        sum(SCORE_WEIGHTS.values()) - 1.0
    ) < 1e-9


# ============================================================
# BUFFER SUPPORT
# ============================================================


def test_event_distance_accepts_buffer():

    candidate = slot(
        12,
        10,
        12,
    )

    without_buffer = score_event_distance(
        candidate,
        previous_busy_end=dt(12, 9),
        next_busy_start=dt(12, 13),
        buffer_minutes=0,
    )

    with_buffer = score_event_distance(
        candidate,
        previous_busy_end=dt(12, 9),
        next_busy_start=dt(12, 13),
        buffer_minutes=30,
    )

    assert without_buffer >= with_buffer