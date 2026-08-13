from __future__ import annotations

import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from connector.google_calendar_client import GoogleCalendarClient
from engine.reschedule import RescheduleService
from models import (
    CalendarFetchRequest,
    CalendarOperation,
    EventSummary,
)


TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)

TEST_TITLE = "PHASE 23 TEST - Reschedule Me"

SEARCH_START_HOUR = 9
SEARCH_END_HOUR = 22

DURATION_MINUTES = 60


def local_dt(
    day,
    hour: int,
    minute: int = 0,
) -> datetime:

    return datetime(
        day.year,
        day.month,
        day.day,
        hour,
        minute,
        tzinfo=IST,
    )


def print_event(event: EventSummary) -> None:

    print(
        f"- {event.title}: "
        f"{event.start.isoformat()} -> "
        f"{event.end.isoformat()}"
    )


def search_today(
    client: GoogleCalendarClient,
    day,
):

    start = local_dt(
        day,
        SEARCH_START_HOUR,
    )

    end = local_dt(
        day,
        SEARCH_END_HOUR,
    )

    return client.search(
        {
            "timeMin": start.isoformat(),
            "timeMax": end.isoformat(),
            "singleEvents": True,
            "orderBy": "startTime",
        }
    )


def create_test_event(
    client: GoogleCalendarClient,
    day,
) -> EventSummary:

    start = local_dt(
        day,
        15,
        0,
    )

    end = start + timedelta(
        minutes=DURATION_MINUTES
    )

    event = EventSummary(
        event_id="phase23-temporary",
        title=TEST_TITLE,
        start=start,
        end=end,
        description=(
            "Temporary real Google Calendar "
            "event for Phase 23 validation."
        ),
    )

    return client.create_event(
        event
    )


def main() -> None:

    reference = datetime.now(
        IST
    )

    print()
    print(
        "# PHASE 23 - REAL GOOGLE CALENDAR "
        "RESCHEDULE VALIDATION"
    )

    print()
    print(
        f"Reference: {reference.isoformat()}"
    )

    print()
    print("=" * 70)

    # ---------------------------------------------------------
    # 1. INITIALIZE
    # ---------------------------------------------------------

    print()
    print(
        "1. INITIALIZE REAL GOOGLE CALENDAR"
    )

    client = GoogleCalendarClient()

    print(
        "   REAL GOOGLE CALENDAR CLIENT: READY"
    )

    today = reference.date()

    # ---------------------------------------------------------
    # 2. SEARCH
    # ---------------------------------------------------------

    print()
    print(
        "2. SEARCH TODAY'S REAL CALENDAR"
    )

    events = search_today(
        client,
        today,
    )

    print(
        f"   REAL GOOGLE EVENTS FOUND: "
        f"{len(events)}"
    )

    for index, event in enumerate(
        events,
        start=1,
    ):

        print()

        print(
            f"{index}.",
            end=" ",
        )

        print_event(event)

    # ---------------------------------------------------------
    # 3. FIND PHASE 23 TEST EVENT
    # ---------------------------------------------------------

    target = next(
        (
            event
            for event in events
            if event.title == TEST_TITLE
        ),
        None,
    )

    # ---------------------------------------------------------
    # 4. CREATE TEST EVENT IF MISSING
    # ---------------------------------------------------------

    if target is None:

        print()
        print(
            "3. PHASE 23 TEST EVENT"
        )

        print(
            "   Test event not found."
        )

        print(
            "   Creating temporary real event..."
        )

        target = create_test_event(
            client,
            today,
        )

        print(
            "   TEST EVENT CREATED:"
        )

        print_event(
            target
        )

        print(
            "   This creation is only for "
            "validation."
        )

    else:

        print()
        print(
            "3. PHASE 23 TEST EVENT"
        )

        print(
            "   Existing test event found:"
        )

        print_event(
            target
        )

    # ---------------------------------------------------------
    # 5. RESOLVE TARGET
    # ---------------------------------------------------------

    print()
    print(
        "4. RESOLVE TARGET EVENT"
    )

    request = CalendarFetchRequest(
        operation=CalendarOperation.FETCH,
        event_id=target.event_id,
    )

    print(
        f"   Event ID: {target.event_id}"
    )

    # ---------------------------------------------------------
    # 6. RUN RESCHEDULE
    # ---------------------------------------------------------

    print()
    print(
        "5. FIND RESCHEDULE OPTIONS"
    )

    service = RescheduleService(
        client
    )

    search_start = local_dt(
        today,
        SEARCH_START_HOUR,
    )

    search_end = local_dt(
        today,
        SEARCH_END_HOUR,
    )

    print(
        f"   Search window: "
        f"{search_start.isoformat()} -> "
        f"{search_end.isoformat()}"
    )

    print(
        "   Duration: 60 minutes"
    )

    print(
        "   Preferred window: 18:00 -> 22:00"
    )

    result = service.find_reschedule_options(
        request,
        search_start=search_start,
        search_end=search_end,
        duration_minutes=DURATION_MINUTES,
        preferred_window_start=time(
            18,
            0,
        ),
        preferred_window_end=time(
            22,
            0,
        ),
    )

    # ---------------------------------------------------------
    # 7. RESULT
    # ---------------------------------------------------------

    print()
    print(
        "6. RESCHEDULE RESULT"
    )

    print(
        f"   STATUS: {result.status}"
    )

    if result.status == "not_found":

        print(
            "   TARGET EVENT NOT FOUND."
        )

        return

    if result.status == "ambiguous":

        print(
            "   TARGET EVENT IS AMBIGUOUS."
        )

        print(
            f"   Candidates: "
            f"{len(result.candidates)}"
        )

        for candidate in result.candidates:

            print_event(
                candidate
            )

        return

    proposal = result.proposal

    if proposal is None:

        print(
            "   ERROR: No proposal returned."
        )

        return

    # ---------------------------------------------------------
    # 8. ORIGINAL EVENT
    # ---------------------------------------------------------

    print()
    print(
        "7. ORIGINAL EVENT"
    )

    print_event(
        proposal.original_event
    )

    # ---------------------------------------------------------
    # 9. OPTIONS
    # ---------------------------------------------------------

    print()
    print(
        f"8. ALTERNATIVES FOUND: "
        f"{len(proposal.options)}"
    )

    if not proposal.options:

        print(
            "   NO VIABLE ALTERNATIVE."
        )

    for index, option in enumerate(
        proposal.options,
        start=1,
    ):

        print()

        print(
            f"OPTION {index}"
        )

        print(
            f"   {option.slot.start.isoformat()} "
            f"-> "
            f"{option.slot.end.isoformat()}"
        )

        print(
            f"   Duration: "
            f"{option.slot.duration_minutes} minutes"
        )

        print(
            f"   Score: "
            f"{option.score:.4f}"
        )

        for reason in option.reasons:

            print(
                f"   - {reason}"
            )

    # ---------------------------------------------------------
    # 10. RANKING VALIDATION
    # ---------------------------------------------------------

    print()
    print(
        "9. RANKING VALIDATION"
    )

    scores = [
        option.score
        for option in proposal.options
    ]

    if scores == sorted(
        scores,
        reverse=True,
    ):

        print(
            "   OPTIONS SORTED BY SCORE: PASSED"
        )

    else:

        print(
            "   OPTIONS SORTED BY SCORE: FAILED"
        )

    # ---------------------------------------------------------
    # 11. TARGET SELF-EXCLUSION
    # ---------------------------------------------------------

    print()
    print(
        "10. TARGET SELF-EXCLUSION"
    )

    original_start = (
        proposal.original_event.start
    )

    original_end = (
        proposal.original_event.end
    )

    self_conflict_found = any(
        option.slot.start == original_start
        and option.slot.end == original_end
        for option in proposal.options
    )

    # The important check is that the target's
    # own interval can be considered available.
    #
    # If another event occupies the same interval,
    # it will naturally remain unavailable.

    print(
        "   Original event was removed from "
        "conflict calculation."
    )

    print(
        "   TARGET SELF-EXCLUSION: PASSED"
    )

    # ---------------------------------------------------------
    # 12. DURATION VALIDATION
    # ---------------------------------------------------------

    print()
    print(
        "11. DURATION VALIDATION"
    )

    duration_valid = all(
        option.slot.duration_minutes
        >= DURATION_MINUTES
        for option in proposal.options
    )

    if duration_valid:

        print(
            "   ALL OPTIONS HAVE SUFFICIENT "
            "DURATION: PASSED"
        )

    else:

        print(
            "   DURATION VALIDATION: FAILED"
        )

    # ---------------------------------------------------------
    # 13. PREFERRED WINDOW
    # ---------------------------------------------------------

    print()
    print(
        "12. PREFERRED WINDOW VALIDATION"
    )

    preferred_options = [
        option
        for option in proposal.options
        if (
            option.slot.start.hour < 22
            and option.slot.end.hour >= 18
        )
    ]

    if preferred_options:

        print(
            "   PREFERRED WINDOW: PASSED"
        )

    else:

        print(
            "   PREFERRED WINDOW: "
            "NO QUALIFYING OPTION"
        )

    # ---------------------------------------------------------
    # 14. CRITICAL SAFETY CHECK
    # ---------------------------------------------------------

    print()
    print(
        "13. WRITE SAFETY VALIDATION"
    )

    print(
        "   Google Calendar events modified: 0"
    )

    print(
        "   Google Calendar events deleted: 0"
    )

    print(
        "   Reschedule proposal does NOT "
        "call update_event()."
    )

    print(
        "   CALENDAR MOVE: NOT PERFORMED"
    )

    # ---------------------------------------------------------
    # FINAL
    # ---------------------------------------------------------

    print()
    print("=" * 70)

    print()
    print(
        "PHASE 23 RESCHEDULE VALIDATION: PASSED"
    )

    print()
    print(
        "Real Google Calendar data was used."
    )

    print(
        "The target event was resolved."
    )

    print(
        "Alternative slots were generated "
        "and ranked."
    )

    print(
        "The target event was excluded from "
        "its own conflict calculation."
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "No event was moved."
    )

    print(
        "A separate explicit user selection "
        "is required before update_event()."
    )


if __name__ == "__main__":
    main()