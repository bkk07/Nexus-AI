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


def dt(hour: int, minute: int = 0) -> datetime:
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


def fetch_by_id(
    event_id: str,
) -> CalendarFetchRequest:
    return CalendarFetchRequest(
        operation=CalendarOperation.FETCH,
        event_id=event_id,
    )


def fetch_by_query(
    query: str,
) -> CalendarFetchRequest:
    return CalendarFetchRequest(
        operation=CalendarOperation.FETCH,
        query=query,
    )


class FakeCalendarClient:
    """
    Integration-test calendar connector.

    This intentionally behaves like the connector interface
    without making any Google Calendar API calls.
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

        # Phase 13 fetch/search.
        if "q" in query:

            text = query["q"].lower()

            return [
                item
                for item in self.events
                if text in item.title.lower()
            ]

        # Reschedule availability search.
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
            "Reschedule option generation must "
            "not update the calendar."
        )

    def create_event(
        self,
        event: EventSummary,
    ) -> EventSummary:

        self.create_calls += 1

        raise AssertionError(
            "Reschedule option generation must "
            "not create events."
        )

    def delete_event(
        self,
        event_id: str,
    ) -> None:

        self.delete_calls += 1

        raise AssertionError(
            "Reschedule option generation must "
            "not delete events."
        )


def build_service(
    events: list[EventSummary],
):
    client = FakeCalendarClient(events)

    service = RescheduleService(
        client
    )

    return service, client


# ============================================================
# 1. "I can't attend my 3 PM meeting.
#    Find another time."
# ============================================================


def test_cannot_attend_3pm_meeting_finds_another_time():

    meeting = event(
        "meeting-3pm",
        "3 PM Meeting",
        15,
        16,
    )

    busy_1 = event(
        "busy-1",
        "Morning Meeting",
        10,
        11,
    )

    busy_2 = event(
        "busy-2",
        "Afternoon Meeting",
        13,
        14,
    )

    service, client = build_service(
        [
            meeting,
            busy_1,
            busy_2,
        ]
    )

    result = service.find_reschedule_options(
        fetch_by_id(
            "meeting-3pm"
        ),
        search_start=dt(9),
        search_end=dt(22),
        duration_minutes=60,
    )

    assert result.status == "found"

    assert result.proposal is not None

    assert (
        result.proposal.original_event.event_id
        == "meeting-3pm"
    )

    assert len(
        result.proposal.options
    ) > 0

    # The original event is not itself a conflict.
    assert any(
        option.slot.start <= dt(15)
        and option.slot.end >= dt(16)
        for option in result.proposal.options
    )

    # No write operation occurred.
    assert client.update_calls == 0
    assert client.create_calls == 0
    assert client.delete_calls == 0


# ============================================================
# 2. "Move my 3 PM meeting to another time."
# ============================================================

def test_move_3pm_meeting_returns_ranked_alternatives():

    meeting = event(
        "meeting-3pm",
        "3 PM Meeting",
        15,
        16,
    )

    busy = event(
        "busy",
        "Existing Meeting",
        10,
        11,
    )

    service, client = build_service(
        [
            meeting,
            busy,
        ]
    )

    result = service.find_reschedule_options(
        fetch_by_id(
            "meeting-3pm"
        ),
        search_start=dt(9),
        search_end=dt(22),
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

    # Ranked highest score first.
    scores = [
        option.score
        for option in options
    ]

    assert scores == sorted(
        scores,
        reverse=True,
    )

    # At least one candidate must overlap
    # the preferred 18:00 -> 22:00 window.
    #
    # We intentionally do NOT require the slot
    # to start at 18:00 because Phase 10 can return
    # the complete free interval.

    preferred_options = [
        option
        for option in options
        if (
            option.slot.start < dt(22)
            and option.slot.end > dt(18)
        )
    ]

    assert preferred_options

    # The preferred-window candidates should have
    # a positive preference contribution.
    assert any(
        "time preference score=1.000"
        in reason
        or "time preference score="
        in reason
        for option in preferred_options
        for reason in option.reasons
    )

    # Generating alternatives must never modify
    # the calendar.
    assert client.update_calls == 0

    assert client.create_calls == 0

    assert client.delete_calls == 0

# ============================================================
# 3. "Reschedule my DSA session."
#
# Ambiguous target -> ask user to choose first.
# ============================================================


def test_reschedule_dsa_session_requires_disambiguation():

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

    service, client = build_service(
        [
            dsa_1,
            dsa_2,
        ]
    )

    result = service.find_reschedule_options(
        fetch_by_query(
            "DSA Session"
        ),
        search_start=dt(9),
        search_end=dt(22),
        duration_minutes=60,
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

    # We must not search/update/reschedule
    # before the user chooses the target.
    assert client.update_calls == 0


# ============================================================
# 4. "Find another time for my project meeting."
# ============================================================


def test_project_meeting_returns_alternatives():

    project = event(
        "project",
        "Project Meeting",
        15,
        17,
    )

    busy_1 = event(
        "busy-1",
        "Morning Meeting",
        9,
        11,
    )

    busy_2 = event(
        "busy-2",
        "Lunch Meeting",
        13,
        14,
    )

    service, client = build_service(
        [
            project,
            busy_1,
            busy_2,
        ]
    )

    result = service.find_reschedule_options(
        fetch_by_id(
            "project"
        ),
        search_start=dt(9),
        search_end=dt(22),
        duration_minutes=120,
    )

    assert result.status == "found"

    assert result.proposal is not None

    assert (
        result.proposal.original_event.event_id
        == "project"
    )

    assert len(
        result.proposal.options
    ) > 0

    # Every alternative must accommodate
    # the complete two-hour duration.
    for option in result.proposal.options:

        duration = int(
            (
                option.slot.end
                - option.slot.start
            ).total_seconds()
            // 60
        )

        assert duration >= 120

    assert client.update_calls == 0


# ============================================================
# 5. No viable alternative.
# ============================================================


def test_reschedule_reports_no_viable_alternative():

    target = event(
        "target",
        "Project Meeting",
        15,
        16,
    )

    blocker = event(
        "blocker",
        "Replacement Blocker",
        15,
        16,
    )

    service, client = build_service(
        [
            target,
            blocker,
        ]
    )

    result = service.find_reschedule_options(
        fetch_by_id(
            "target"
        ),
        search_start=dt(15),
        search_end=dt(16),
        duration_minutes=60,
    )

    assert result.status == "found"

    assert result.proposal is not None

    assert (
        result.proposal.options
        == []
    )

    assert (
        "No viable alternative"
        in result.message
    )

    assert client.update_calls == 0


# ============================================================
# 6. Explicit selection/update is NOT part of
#    find_reschedule_options().
# ============================================================


def test_reschedule_proposal_does_not_move_event():

    target = event(
        "target",
        "DSA Session",
        15,
        16,
    )

    service, client = build_service(
        [target]
    )

    result = service.find_reschedule_options(
        fetch_by_id(
            "target"
        ),
        search_start=dt(9),
        search_end=dt(22),
        duration_minutes=60,
    )

    assert result.proposal is not None

    assert result.proposal.options

    # The event remains untouched.
    assert client.update_calls == 0

    assert client.create_calls == 0

    assert client.delete_calls == 0

    # The proposal is merely an option list.
    assert (
        result.proposal.original_event.start
        == dt(15)
    )

    assert (
        result.proposal.original_event.end
        == dt(16)
    )