from datetime import datetime, time
from zoneinfo import ZoneInfo

from best_slot import BestSlotService
from free_slot_service import FreeSlotService
from models import EventSummary


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


def make_event(
    event_id: str,
    start: datetime,
    end: datetime,
) -> EventSummary:

    return EventSummary(
        event_id=event_id,
        title=f"Event {event_id}",
        start=start,
        end=end,
    )


def test_best_two_hour_dsa_slot_tomorrow():
    """
    Integration scenario:

        "Find the best 2 hour slot tomorrow for DSA."

    The fixture calendar contains several free slots with
    different qualities.

    The expected winner is the evening slot because the
    request has an evening preference.
    """

    events = [
        # Morning busy block
        make_event(
            "busy-1",
            dt(13, 9),
            dt(13, 10),
        ),

        # Afternoon busy block
        make_event(
            "busy-2",
            dt(13, 13),
            dt(13, 14),
        ),

        # Evening busy block
        make_event(
            "busy-3",
            dt(13, 20),
            dt(13, 21),
        ),
    ]

    free_service = FreeSlotService()

    candidates = free_service.find_free_slots(
        events=events,
        window=__import__(
            "datetime_utils"
        ).DateTimeRange(
            start=dt(13, 8),
            end=dt(13, 22),
        ),
        minimum_duration_minutes=120,
    )

    assert len(candidates) > 1

    best_service = BestSlotService()

    ranked = best_service.rank_slots(
        slots=candidates,
        requested_duration_minutes=120,
        preferred_start=time(18, 0),
    )

    assert ranked

    best = ranked[0]

    assert best.slot.start == dt(13, 14)
    assert best.slot.end == dt(13, 20)

    assert best.slot.duration_minutes == 360

    assert best.score > 0

    assert best.reasons

    assert all(
        isinstance(reason, str)
        for reason in best.reasons
    )


def test_full_ranked_list_is_returned():

    events = [
        make_event(
            "busy-1",
            dt(13, 9),
            dt(13, 10),
        ),
        make_event(
            "busy-2",
            dt(13, 13),
            dt(13, 14),
        ),
        make_event(
            "busy-3",
            dt(13, 20),
            dt(13, 21),
        ),
    ]

    free_service = FreeSlotService()

    from datetime_utils import DateTimeRange

    candidates = free_service.find_free_slots(
        events=events,
        window=DateTimeRange(
            start=dt(13, 8),
            end=dt(13, 22),
        ),
        minimum_duration_minutes=120,
    )

    service = BestSlotService()

    ranked = service.rank_slots(
        slots=candidates,
        requested_duration_minutes=120,
        preferred_start=time(18, 0),
    )

    assert len(ranked) == len(candidates)

    scores = [
        item.score
        for item in ranked
    ]

    assert scores == sorted(
        scores,
        reverse=True,
    )


def test_ranking_is_deterministic():

    candidates = [
        # 09:00 -> 13:00
        #
        # 4-hour slot
        #
        # valid for a 2-hour request.
        #
        # 18:00 -> 20:00
        #
        # exact 2-hour slot.
        #
        # Evening preference should make this attractive.
        #
    ]

    from models import TimeSlot

    candidates = [
        TimeSlot(
            start=dt(13, 9),
            end=dt(13, 13),
            duration_minutes=240,
        ),
        TimeSlot(
            start=dt(13, 18),
            end=dt(13, 20),
            duration_minutes=120,
        ),
    ]

    service = BestSlotService()

    first = service.rank_slots(
        slots=candidates,
        requested_duration_minutes=120,
        preferred_start=time(18, 0),
    )

    second = service.rank_slots(
        slots=candidates,
        requested_duration_minutes=120,
        preferred_start=time(18, 0),
    )

    assert [
        (
            item.slot.start,
            item.slot.end,
            item.score,
            item.reasons,
        )
        for item in first
    ] == [
        (
            item.slot.start,
            item.slot.end,
            item.score,
            item.reasons,
        )
        for item in second
    ]


def test_no_candidates_returns_none():

    service = BestSlotService()

    result = service.find_best_slot(
        slots=[],
        requested_duration_minutes=120,
        preferred_start=time(18, 0),
    )

    assert result is None


def test_single_candidate_still_has_reasons():

    from models import TimeSlot

    candidate = TimeSlot(
        start=dt(13, 18),
        end=dt(13, 20),
        duration_minutes=120,
    )

    service = BestSlotService()

    result = service.find_best_slot(
        slots=[candidate],
        requested_duration_minutes=120,
        preferred_start=time(18, 0),
    )

    assert result is not None

    assert result.slot == candidate

    assert result.reasons

    assert result.score > 0