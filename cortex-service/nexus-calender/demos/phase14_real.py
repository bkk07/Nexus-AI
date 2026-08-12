from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


# =========================================================
# PROJECT PATH
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================
# PROJECT IMPORTS
# =========================================================

from compiler import CalendarQueryCompiler
from connector.google_calendar_client import GoogleCalendarClient
from engine.search import CalendarSearchEngine
from engine.update import CalendarUpdateService

from models import (
    CalendarOperation,
    CalendarRequest,
    CalendarUpdateRequest,
)


# =========================================================
# CONFIG
# =========================================================

TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)

TEMP_TITLE = "NEXUS PHASE 14 TEMP EVENT"


# =========================================================
# HELPERS
# =========================================================

def today_at(
    hour: int,
    minute: int = 0,
) -> datetime:

    now = datetime.now(IST)

    return now.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )


def print_event(event) -> None:

    print(
        f"{event.title}: "
        f"{event.start.isoformat()} -> "
        f"{event.end.isoformat()}"
    )


# =========================================================
# MAIN
# =========================================================

def main() -> None:

    print("=" * 70)
    print("PHASE 14 - REAL GOOGLE CALENDAR UPDATE VALIDATION")
    print("=" * 70)

    reference = datetime.now(IST)

    print()
    print("Reference:")
    print(reference.isoformat())

    # =====================================================
    # REAL GOOGLE CLIENT
    # =====================================================

    client = GoogleCalendarClient(
        calendar_id="primary",
    )

    compiler = CalendarQueryCompiler(
        default_timezone=TIMEZONE,
        default_search_days=30,
    )

    search_engine = CalendarSearchEngine(
        client=client,
        compiler=compiler,
    )

    update_service = CalendarUpdateService(
        client=client,
    )

    # =====================================================
    # 1. SEARCH TODAY'S CALENDAR
    # =====================================================

    print()
    print("=" * 70)
    print("1. SEARCH TODAY'S REAL CALENDAR")
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

    for index, event in enumerate(
        events,
        start=1,
    ):

        print(
            f"{index}. ",
            end="",
        )

        print_event(event)

    # =====================================================
    # 2. FIND A FREE TEMPORARY TIME
    # =====================================================

    print()
    print("=" * 70)
    print("2. SELECT TEMPORARY TEST TIME")
    print("=" * 70)

    # Use late-night time to minimize the chance of collision.
    #
    # If 23:00 is already occupied, try 23:30.
    # If both are occupied, try 22:30.

    candidate_starts = [
        today_at(23, 0),
        today_at(23, 30),
        today_at(22, 30),
    ]

    temporary_start = None
    temporary_end = None

    for candidate in candidate_starts:

        candidate_end = (
            candidate
            + timedelta(minutes=30)
        )

        conflict = False

        for event in events:

            if (
                candidate < event.end
                and candidate_end > event.start
            ):
                conflict = True
                break

        if not conflict:

            temporary_start = candidate
            temporary_end = candidate_end

            break

    if (
        temporary_start is None
        or temporary_end is None
    ):

        print(
            "Could not find a free 30-minute "
            "temporary test slot today."
        )

        return

    print(
        "Temporary test slot:"
    )

    print(
        f"{temporary_start.isoformat()} "
        f"-> "
        f"{temporary_end.isoformat()}"
    )

    # =====================================================
    # 3. CREATE TEMPORARY EVENT
    #
    # This is ONLY test setup.
    # =====================================================

    print()
    print("=" * 70)
    print("3. CREATE TEMPORARY TEST EVENT")
    print("=" * 70)

    temporary_event = None

    try:

        temporary_event = client.create_event(
            # EventSummary-like object
            type(
                "TemporaryEvent",
                (),
                {
                    "event_id": "",
                    "title": TEMP_TITLE,
                    "start": temporary_start,
                    "end": temporary_end,
                    "location": None,
                    "description": (
                        "Temporary event for "
                        "Phase 14 validation."
                    ),
                },
            )()
        )

        print(
            f"Status: created"
        )

        print(
            f"Created event ID: "
            f"{temporary_event.event_id}"
        )

        print_event(
            temporary_event
        )

    except Exception as exc:

        print(
            "TEMPORARY EVENT CREATION FAILED"
        )

        raise exc

    temporary_id = (
        temporary_event.event_id
    )

    # =====================================================
    # 4. VERIFY CREATED EVENT
    # =====================================================

    try:

        print()
        print("=" * 70)
        print("4. VERIFY TEMPORARY EVENT")
        print("=" * 70)

        search_request = CalendarRequest(
            operation=CalendarOperation.SEARCH,
            date="today",
            start_time="00:00",
            end_time="23:59",
        )

        events_after_create = (
            search_engine.search_events(
                search_request,
                reference=datetime.now(IST),
            )
        )

        found = next(
            (
                event
                for event in events_after_create
                if event.event_id
                == temporary_id
            ),
            None,
        )

        assert found is not None

        print(
            f"Found: {found.title}"
        )

        print_event(found)

        print(
            "CREATE VERIFICATION: PASSED"
        )

        # =================================================
        # 5. UPDATE TITLE
        # =================================================

        print()
        print("=" * 70)
        print("5. UPDATE TITLE")
        print("=" * 70)

        title_update = CalendarUpdateRequest(
            operation=CalendarOperation.UPDATE,
            event_id=temporary_id,
            new_title=(
                "NEXUS PHASE 14 UPDATED EVENT"
            ),
        )

        result = update_service.update(
            title_update,
            events_after_create,
        )

        print(
            f"Status: {result.status}"
        )

        print(
            f"Message: {result.message}"
        )

        assert result.status == "updated"

        assert result.event is not None

        print(
            f"Updated title: "
            f"{result.event.title}"
        )

        print(
            "TITLE UPDATE: PASSED"
        )

        # =================================================
        # 6. VERIFY TITLE UPDATE
        # =================================================

        print()
        print("=" * 70)
        print("6. VERIFY TITLE UPDATE")
        print("=" * 70)

        events_after_title = (
            search_engine.search_events(
                search_request,
                reference=datetime.now(IST),
            )
        )

        updated_event = next(
            (
                event
                for event in events_after_title
                if event.event_id
                == temporary_id
            ),
            None,
        )

        assert updated_event is not None

        assert (
            updated_event.title
            == "NEXUS PHASE 14 UPDATED EVENT"
        )

        print(
            f"Verified title: "
            f"{updated_event.title}"
        )

        print(
            "TITLE VERIFICATION: PASSED"
        )

        # =================================================
        # 7. UPDATE TIME TO ANOTHER FREE SLOT
        # =================================================

        print()
        print("=" * 70)
        print("7. UPDATE TIME")
        print("=" * 70)

        new_start = (
            temporary_end
        )

        new_end = (
            new_start
            + timedelta(minutes=30)
        )

        # Make sure the new location does not overlap
        # with another real event.

        for event in events_after_title:

            if event.event_id == temporary_id:
                continue

            if (
                new_start < event.end
                and new_end > event.start
            ):

                new_start = (
                    new_start
                    + timedelta(minutes=30)
                )

                new_end = (
                    new_start
                    + timedelta(minutes=30)
                )

        time_update = CalendarUpdateRequest(
            operation=CalendarOperation.UPDATE,
            event_id=temporary_id,
            new_start=new_start,
            new_end=new_end,
        )

        result = update_service.update(
            time_update,
            events_after_title,
        )

        print(
            f"Status: {result.status}"
        )

        print(
            f"Message: {result.message}"
        )

        assert result.status == "updated"

        assert result.event is not None

        print(
            f"New time: "
            f"{result.event.start.isoformat()} "
            f"-> "
            f"{result.event.end.isoformat()}"
        )

        print(
            "TIME UPDATE: PASSED"
        )

        # =================================================
        # 8. VERIFY TIME UPDATE
        # =================================================

        print()
        print("=" * 70)
        print("8. VERIFY TIME UPDATE")
        print("=" * 70)

        events_after_time = (
            search_engine.search_events(
                search_request,
                reference=datetime.now(IST),
            )
        )

        moved_event = next(
            (
                event
                for event in events_after_time
                if event.event_id
                == temporary_id
            ),
            None,
        )

        assert moved_event is not None

        assert (
            moved_event.start
            == new_start
        )

        assert (
            moved_event.end
            == new_end
        )

        print(
            f"Verified time: "
            f"{moved_event.start.isoformat()} "
            f"-> "
            f"{moved_event.end.isoformat()}"
        )

        print(
            "TIME VERIFICATION: PASSED"
        )

        # =================================================
        # 9. CONFLICTING UPDATE
        # =================================================

        print()
        print("=" * 70)
        print("9. CONFLICTING UPDATE")
        print("=" * 70)

        # Find a real event that we can conflict with.

        conflict_event = next(
            (
                event
                for event in events_after_time
                if event.event_id
                != temporary_id
            ),
            None,
        )

        if conflict_event is None:

            print(
                "No other real event available "
                "for conflict validation."
            )

            print(
                "CONFLICT TEST: SKIPPED"
            )

        else:

            print(
                "Existing event:"
            )

            print_event(
                conflict_event
            )

            conflict_update = (
                CalendarUpdateRequest(
                    operation=(
                        CalendarOperation.UPDATE
                    ),
                    event_id=temporary_id,
                    new_start=(
                        conflict_event.start
                    ),
                    new_end=(
                        conflict_event.end
                    ),
                )
            )

            result = (
                update_service.update(
                    conflict_update,
                    events_after_time,
                )
            )

            print(
                f"Status: {result.status}"
            )

            print(
                f"Message: {result.message}"
            )

            assert (
                result.status
                == "conflict_blocked"
            )

            assert result.event is None

            assert len(
                result.conflicts
            ) > 0

            print(
                "CONFLICT BLOCKING: PASSED"
            )

            # =============================================
            # 10. VERIFY BLOCKED UPDATE DID NOT CHANGE
            # =============================================

            print()
            print("=" * 70)
            print(
                "10. VERIFY BLOCKED UPDATE "
                "DID NOT CHANGE EVENT"
            )
            print("=" * 70)

            events_after_block = (
                search_engine.search_events(
                    search_request,
                    reference=datetime.now(IST),
                )
            )

            unchanged_event = next(
                (
                    event
                    for event
                    in events_after_block
                    if event.event_id
                    == temporary_id
                ),
                None,
            )

            assert unchanged_event is not None

            assert (
                unchanged_event.start
                == new_start
            )

            assert (
                unchanged_event.end
                == new_end
            )

            print(
                f"Event remains at: "
                f"{unchanged_event.start.isoformat()} "
                f"-> "
                f"{unchanged_event.end.isoformat()}"
            )

            print(
                "NO-WRITE CONFLICT VERIFICATION: PASSED"
            )

    finally:

        # =================================================
        # 11. CLEANUP
        # =================================================

        print()
        print("=" * 70)
        print("11. CLEANUP")
        print("=" * 70)

        if temporary_event is not None:

            print(
                f"Deleting temporary event: "
                f"{temporary_id}"
            )

            client.delete_event(
                temporary_id
            )

            print(
                "Temporary event deleted."
            )

            # =============================================
            # 12. VERIFY CLEANUP
            # =============================================

            events_after_cleanup = (
                search_engine.search_events(
                    CalendarRequest(
                        operation=(
                            CalendarOperation.SEARCH
                        ),
                        date="today",
                        start_time="00:00",
                        end_time="23:59",
                    ),
                    reference=datetime.now(IST),
                )
            )

            still_exists = any(
                event.event_id
                == temporary_id
                for event
                in events_after_cleanup
            )

            assert not still_exists

            print(
                "Temporary event no longer exists."
            )

            print(
                "CLEANUP VERIFICATION: PASSED"
            )

    # =====================================================
    # FINAL
    # =====================================================

    print()
    print("=" * 70)
    print(
        "PHASE 14 REAL GOOGLE VALIDATION: PASSED"
    )
    print("=" * 70)

    print()
    print(
        "Temporary Google Calendar event "
        "was cleaned up."
    )


if __name__ == "__main__":
    main()