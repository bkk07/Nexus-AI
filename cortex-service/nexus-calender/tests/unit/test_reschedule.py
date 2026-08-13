from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from engine.reschedule import RescheduleService
from models import (
    CalendarFetchRequest,
    CalendarOperation,
    EventSummary,
)


IST = ZoneInfo("Asia/Kolkata")


def dt(
    hour: int,
    minute: int = 0,
) -> datetime:
    return datetime(
        2026,
        8,
        13,
        hour,
        minute,
        tzinfo=IST,
    )


def event(
    event_id: str,
    title: str,
    start_hour: int,
    end_hour: int,
) -> EventSummary:
    return EventSummary(
        event_id=event_id,
        title=title,
        start=dt(start_hour),
        end=dt(end_hour),
    )


def fetch_request(
    *,
    event_id: str | None = None,
    query: str | None = None,
) -> CalendarFetchRequest:
    return CalendarFetchRequest(
        operation=CalendarOperation.FETCH,
        event_id=event_id,
        query=query,
    )


class FakeCalendarClient:
    """
    Fake calendar connector.

    No real Google Calendar API calls are made.
    """

    def __init__(
        self,
        events: list[EventSummary],
    ) -> None:
        self.events = events

        self.update_calls = 0
        self.create_calls = 0
        self.delete_calls = 0

    def get_event(
        self,
        event_id: str,
    ) -> EventSummary | None:

        for item in self.events:
            if item.event_id == event_id:
                return item

        return None

    def search(
        self,
        query: dict,
    ) -> list[EventSummary]:

        # --------------------------------------------
        # Fetch/search by text.
        # --------------------------------------------

        if "q" in query:

            text = query["q"].lower()

            return [
                item
                for item in self.events
                if text in item.title.lower()
            ]

        # --------------------------------------------
        # Availability/search by time range.
        # --------------------------------------------

        time_min = datetime.fromisoformat(
            query["timeMin"]
        )

        time_max = datetime.fromisoformat(
            query["timeMax"]
        )

        return [
            item
            for item in self.events
            if (
                item.start < time_max
                and item.end > time_min
            )
        ]

    def update_event(
        self,
        event: EventSummary,
    ) -> EventSummary:

        self.update_calls += 1

        raise AssertionError(
            "update_event() must never be called "
            "while generating reschedule options."
        )

    def create_event(
        self,
        event: EventSummary,
    ) -> EventSummary:

        self.create_calls += 1

        raise AssertionError(
            "create_event() must not be called."
        )

    def delete_event(
        self,
        event_id: str,
    ) -> None:

        self.delete_calls += 1

        raise AssertionError(
            "delete_event() must not be called."
        )


def search_start() -> datetime:
    return dt(9)


def search_end() -> datetime:
    return dt(22)


# ============================================================
# 1. TARGET EVENT SELF-EXCLUSION
# ============================================================


def test_target_event_is_excluded_from_own_conflict_check():

    target = event(
        "meeting-1",
        "DSA Meeting",
        15,
        16,
    )

    other = event(
        "meeting-2",
        "Other Meeting",
        10,
        11,
    )

    client = FakeCalendarClient(
        [
            target,
            other,
        ]
    )

    service = RescheduleService(
        client
    )

    result = service.find_reschedule_options(
        fetch_request(
            event_id="meeting-1"
        ),
        search_start=search_start(),
        search_end=search_end(),
    )

    assert result.status == "found"

    assert result.proposal is not None

    assert (
        result.proposal.original_event.event_id
        == "meeting-1"
    )

    assert result.proposal.options

    # The original event must not block its own
    # time interval.
    #
    # Phase 10 ranking keeps the complete free slot,
    # so the candidate may be 15:00 -> 22:00 rather
    # than exactly 15:00 -> 16:00.

    matching = [
        option
        for option in result.proposal.options
        if (
            option.slot.start <= dt(15)
            and option.slot.end >= dt(16)
        )
    ]

    assert matching


# ============================================================
# 2. AMBIGUOUS TARGET
# ============================================================


def test_ambiguous_target_returns_candidates_without_proposing():

    dsa_1 = event(
        "dsa-1",
        "DSA Session",
        15,
        16,
    )

    dsa_2 = event(
        "dsa-2",
        "DSA Session",
        18,
        19,
    )

    client = FakeCalendarClient(
        [
            dsa_1,
            dsa_2,
        ]
    )

    service = RescheduleService(
        client
    )

    result = service.find_reschedule_options(
        fetch_request(
            query="DSA Session"
        ),
        search_start=search_start(),
        search_end=search_end(),
    )

    assert result.status == "ambiguous"

    assert result.proposal is None

    assert len(
        result.candidates
    ) == 2

    candidate_ids = {
        candidate.event_id
        for candidate in result.candidates
    }

    assert candidate_ids == {
        "dsa-1",
        "dsa-2",
    }


# ============================================================
# 3. NO VIABLE ALTERNATIVE
# ============================================================
def test_no_viable_alternative_returns_empty_options():

    target = event(
        "meeting-1",
        "Project Meeting",
        15,
        16,
    )

    # The target event is excluded from the conflict
    # check, so its original interval becomes available.
    #
    # Therefore, to test "no alternative", another
    # event must occupy the same interval.
    blocking_event = event(
        "blocking-event",
        "Replacement Blocker",
        15,
        16,
    )

    client = FakeCalendarClient(
        [
            target,
            blocking_event,
        ]
    )

    service = RescheduleService(
        client
    )

    result = service.find_reschedule_options(
        fetch_request(
            event_id="meeting-1"
        ),
        search_start=dt(15),
        search_end=dt(16),
        duration_minutes=60,
    )

    assert result.status == "found"

    assert result.proposal is not None

    assert result.proposal.options == []

    assert (
        "No viable alternative"
        in result.message
    )


# ============================================================
# 4. OPTIONS ARE RANKED
# ============================================================


def test_reschedule_options_are_ranked():

    target = event(
        "target",
        "DSA Session",
        15,
        16,
    )

    morning_busy = event(
        "busy-1",
        "Morning Meeting",
        10,
        11,
    )

    client = FakeCalendarClient(
        [
            target,
            morning_busy,
        ]
    )

    service = RescheduleService(
        client
    )

    result = service.find_reschedule_options(
        fetch_request(
            event_id="target"
        ),
        search_start=search_start(),
        search_end=search_end(),
        duration_minutes=60,
        preferred_window_start=time(
            18,
            0,
        ),
        preferred_window_end=time(
            22,
            0,
        ),
    )

    assert result.status == "found"

    assert result.proposal is not None

    options = (
        result.proposal.options
    )

    assert len(options) > 0

    scores = [
        option.score
        for option in options
    ]

    assert scores == sorted(
        scores,
        reverse=True,
    )


# ============================================================
# 5. ORIGINAL EVENT IS PRESERVED
# ============================================================


def test_original_event_is_preserved_in_proposal():

    target = event(
        "target",
        "Project Meeting",
        15,
        17,
    )

    client = FakeCalendarClient(
        [target]
    )

    service = RescheduleService(
        client
    )

    result = service.find_reschedule_options(
        fetch_request(
            event_id="target"
        ),
        search_start=search_start(),
        search_end=search_end(),
    )

    assert result.proposal is not None

    original = (
        result.proposal.original_event
    )

    assert original.event_id == "target"

    assert original.title == "Project Meeting"

    assert original.start == dt(15)

    assert original.end == dt(17)


# ============================================================
# 6. NO CALENDAR WRITE
# ============================================================


def test_generating_options_never_updates_calendar():

    target = event(
        "target",
        "DSA Session",
        15,
        16,
    )

    client = FakeCalendarClient(
        [target]
    )

    service = RescheduleService(
        client
    )

    result = service.find_reschedule_options(
        fetch_request(
            event_id="target"
        ),
        search_start=search_start(),
        search_end=search_end(),
    )

    assert result.status == "found"

    assert client.update_calls == 0

    assert client.create_calls == 0

    assert client.delete_calls == 0


# ============================================================
# 7. NOT FOUND
# ============================================================


def test_missing_target_returns_not_found():

    client = FakeCalendarClient(
        []
    )

    service = RescheduleService(
        client
    )

    result = service.find_reschedule_options(
        fetch_request(
            event_id="does-not-exist"
        ),
        search_start=search_start(),
        search_end=search_end(),
    )

    assert result.status == "not_found"

    assert result.proposal is None

    assert result.candidates == []


# ============================================================
# 8. EXPLICIT EVENT ID TAKES PRECEDENCE
# ============================================================


def test_explicit_event_id_resolves_target_directly():

    target = event(
        "target",
        "DSA Session",
        15,
        16,
    )

    another = event(
        "another",
        "DSA Session",
        18,
        19,
    )

    client = FakeCalendarClient(
        [
            target,
            another,
        ]
    )

    service = RescheduleService(
        client
    )

    result = service.find_reschedule_options(
        fetch_request(
            event_id="target",
            query="DSA Session",
        ),
        search_start=search_start(),
        search_end=search_end(),
    )

    assert result.status == "found"

    assert result.proposal is not None

    assert (
        result.proposal.original_event.event_id
        == "target"
    )


# ============================================================
# 9. INVALID SEARCH HORIZON
# ============================================================


def test_invalid_search_horizon_is_rejected():

    target = event(
        "target",
        "DSA Session",
        15,
        16,
    )

    client = FakeCalendarClient(
        [target]
    )

    service = RescheduleService(
        client
    )

    try:

        service.find_reschedule_options(
            fetch_request(
                event_id="target"
            ),
            search_start=dt(18),
            search_end=dt(9),
        )

        assert False, (
            "Expected ValueError"
        )

    except ValueError as exc:

        assert (
            "search_end must be after"
            in str(exc)
        )