from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo



import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from compiler import CalendarQueryCompiler
from connector.google_calendar_client import GoogleCalendarClient
from engine.fetch import CalendarFetchService
from engine.search import CalendarSearchEngine
from models import (
    CalendarFetchRequest,
    CalendarOperation,
    CalendarRequest,
)


TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)


def main() -> None:

    print("=" * 70)
    print("PHASE 13 - REAL GOOGLE CALENDAR FETCH VALIDATION")
    print("=" * 70)

    reference = datetime.now(IST)

    print()
    print("Reference:")
    print(reference.isoformat())

    # =========================================================
    # REAL GOOGLE CALENDAR CLIENT
    # =========================================================

    client = GoogleCalendarClient(
        calendar_id="primary",
    )

    fetch_service = CalendarFetchService(
        client=client,
    )

    compiler = CalendarQueryCompiler(
        default_timezone=TIMEZONE,
        default_search_days=30,
    )

    search_engine = CalendarSearchEngine(
        client=client,
        compiler=compiler,
    )

    # =========================================================
    # 1. SEARCH REAL CALENDAR
    #
    # We use tomorrow because your existing test events
    # are already there.
    # =========================================================

    print()
    print("=" * 70)
    print("REAL GOOGLE CALENDAR SEARCH")
    print("=" * 70)

    search_request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="today",
        start_time="00:00",
        end_time="23:59",
    )

    events = search_engine.search_events(
        search_request,
        reference=reference,
    )

    print(
        f"REAL GOOGLE EVENTS FOUND: {len(events)}"
    )

    if not events:

        print(
            "No events found for tomorrow."
        )

        print(
            "Phase 13 cannot perform the "
            "known-event ID validation."
        )

        return

    for index, event in enumerate(
        events,
        start=1,
    ):

        print(
            f"{index}. "
            f"{event.title}: "
            f"{event.start.isoformat()} -> "
            f"{event.end.isoformat()}"
        )

    # =========================================================
    # 2. EXPLICIT EVENT ID
    #
    # Pick the first real event returned by Google.
    # =========================================================

    known_event = events[0]

    print()
    print("=" * 70)
    print("TEST 1 - EXPLICIT EVENT ID")
    print("=" * 70)

    print(
        f"Fetching event ID: "
        f"{known_event.event_id}"
    )

    request = CalendarFetchRequest(
        operation=CalendarOperation.FETCH,
        event_id=known_event.event_id,
    )

    result = fetch_service.fetch(
        request
    )

    print(
        f"Status: {result.status}"
    )

    if result.event is not None:

        print(
            f"Event: {result.event.title}"
        )

        print(
            f"Start: "
            f"{result.event.start.isoformat()}"
        )

        print(
            f"End: "
            f"{result.event.end.isoformat()}"
        )

    assert result.status == "found"

    assert result.event is not None

    assert (
        result.event.event_id
        == known_event.event_id
    )

    print(
        "EXPLICIT ID FETCH: PASSED"
    )

    # =========================================================
    # 3. MISSING EVENT ID
    #
    # This ID should not exist.
    # =========================================================

    print()
    print("=" * 70)
    print("TEST 2 - MISSING EVENT ID")
    print("=" * 70)

    missing_id = (
        "nexus-phase13-event-does-not-exist-"
        "123456789"
    )

    print(
        f"Fetching event ID: {missing_id}"
    )

    request = CalendarFetchRequest(
        operation=CalendarOperation.FETCH,
        event_id=missing_id,
    )

    result = fetch_service.fetch(
        request
    )

    print(
        f"Status: {result.status}"
    )

    assert result.status == "not_found"

    assert result.event is None

    print(
        "MISSING ID FETCH: PASSED"
    )

    # =========================================================
    # 4. UNIQUE SEARCH
    #
    # Use the title of the first event.
    #
    # If multiple events share the title, this naturally
    # becomes the ambiguity case below.
    # =========================================================

    print()
    print("=" * 70)
    print("TEST 3 - SEARCH-BASED FETCH")
    print("=" * 70)

    search_term = known_event.title

    print(
        f"Search query: {search_term}"
    )

    request = CalendarFetchRequest(
        operation=CalendarOperation.FETCH,
        query=search_term,
    )

    result = fetch_service.fetch(
        request
    )

    print(
        f"Status: {result.status}"
    )

    if result.status == "found":

        assert result.event is not None

        print(
            f"Found: {result.event.title}"
        )

        print(
            "UNIQUE SEARCH FETCH: PASSED"
        )

    elif result.status == "ambiguous":

        print(
            f"Multiple matching events: "
            f"{len(result.candidates)}"
        )

        for candidate in result.candidates:

            print(
                f"- {candidate.title}: "
                f"{candidate.start.strftime('%H:%M')} -> "
                f"{candidate.end.strftime('%H:%M')}"
            )

        print(
            "SEARCH RESULT IS AMBIGUOUS."
        )

    else:

        raise AssertionError(
            "Expected the known event to be "
            "found or ambiguous."
        )

    # =========================================================
    # 5. GUARANTEED ZERO-RESULT SEARCH
    # =========================================================

    print()
    print("=" * 70)
    print("TEST 4 - ZERO SEARCH RESULTS")
    print("=" * 70)

    nonexistent_query = (
        "NEXUS_PHASE_13_EVENT_THAT_DOES_NOT_EXIST"
    )

    print(
        f"Search query: {nonexistent_query}"
    )

    request = CalendarFetchRequest(
        operation=CalendarOperation.FETCH,
        query=nonexistent_query,
    )

    result = fetch_service.fetch(
        request
    )

    print(
        f"Status: {result.status}"
    )

    assert result.status == "not_found"

    assert result.event is None

    assert result.candidates == []

    print(
        "ZERO RESULT FETCH: PASSED"
    )

    # =========================================================
    # 6. AMBIGUITY VALIDATION
    #
    # Find a title occurring more than once in the real
    # calendar. If none exists, we report that the real
    # calendar does not currently provide an ambiguity case.
    # =========================================================

    print()
    print("=" * 70)
    print("TEST 5 - REAL CALENDAR AMBIGUITY")
    print("=" * 70)

    title_counts: dict[str, int] = {}

    for event in events:

        normalized = (
            event.title.strip().lower()
        )

        if not normalized:
            continue

        title_counts[normalized] = (
            title_counts.get(
                normalized,
                0,
            )
            + 1
        )

    duplicate_title = next(
        (
            title
            for title, count
            in title_counts.items()
            if count > 1
        ),
        None,
    )

    if duplicate_title is None:

        print(
            "No duplicate event title exists "
            "in tomorrow's real calendar window."
        )

        print(
            "AMBIGUITY TEST: SKIPPED "
            "(no real ambiguous title available)"
        )

    else:

        print(
            f"Ambiguous title found: "
            f"{duplicate_title}"
        )

        request = CalendarFetchRequest(
            operation=CalendarOperation.FETCH,
            query=duplicate_title,
        )

        result = fetch_service.fetch(
            request
        )

        print(
            f"Status: {result.status}"
        )

        print(
            f"Candidates: "
            f"{len(result.candidates)}"
        )

        assert result.status == "ambiguous"

        assert result.event is None

        assert len(
            result.candidates
        ) > 1

        print(
            "AMBIGUITY FETCH: PASSED"
        )

    # =========================================================
    # FINAL
    # =========================================================

    print()
    print("=" * 70)
    print("PHASE 13 REAL GOOGLE VALIDATION: PASSED")
    print("=" * 70)

    print()
    print(
        "No Google Calendar events were created."
    )

    print(
        "No Google Calendar events were modified."
    )

    print(
        "No Google Calendar events were deleted."
    )


if __name__ == "__main__":
    main()