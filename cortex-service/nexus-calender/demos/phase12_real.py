from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from compiler import CalendarQueryCompiler
from connector.calendar_client import CalendarClient
from connector.google_calendar_client import GoogleCalendarClient
from create import CalendarCreateService
from engine.search import CalendarSearchEngine
from models import (
    CalendarCreateRequest,
    CalendarOperation,
    CalendarRequest,
)


TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)


TEST_TITLE = "NEXUS PHASE 12 TEMP EVENT"


def main() -> None:

    print("=" * 70)
    print("PHASE 12 - REAL GOOGLE CALENDAR SAFE CREATE VALIDATION")
    print("=" * 70)

    reference = datetime.now(IST)

    print()
    print("Reference:")
    print(reference.isoformat())

    # =========================================================
    # REAL GOOGLE CALENDAR
    # =========================================================

    client: CalendarClient = GoogleCalendarClient(
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

    create_service = CalendarCreateService(
        client=client,
    )

    # =========================================================
    # TEST DATE
    #
    # Use tomorrow at 23:00 -> 23:30.
    # =========================================================

    tomorrow = reference + timedelta(days=1)

    start = tomorrow.replace(
        hour=23,
        minute=0,
        second=0,
        microsecond=0,
    )

    end = tomorrow.replace(
        hour=23,
        minute=30,
        second=0,
        microsecond=0,
    )

    create_request = CalendarCreateRequest(
        title=TEST_TITLE,
        start=start,
        end=end,
        description="Temporary Nexus AI Phase 12 validation event.",
    )

    print()
    print("=" * 70)
    print("TEMPORARY TEST EVENT")
    print("=" * 70)

    print(
        f"Title: {create_request.title}"
    )

    print(
        f"Start: {create_request.start.isoformat()}"
    )

    print(
        f"End: {create_request.end.isoformat()}"
    )

    temporary_event_id: str | None = None

    try:

        # =====================================================
        # 1. SEARCH EXISTING EVENTS
        # =====================================================

        search_request = CalendarRequest(
            operation=CalendarOperation.SEARCH,
            date="tomorrow",
            start_time="00:00",
            end_time="23:59",
        )

        existing_events = search_engine.search_events(
            search_request,
            reference=reference,
        )

        print()
        print("=" * 70)
        print("INITIAL REAL CALENDAR SEARCH")
        print("=" * 70)

        print(
            f"Events found: {len(existing_events)}"
        )

        # =====================================================
        # SAFETY CHECK
        #
        # If an old temporary event exists from a previous
        # interrupted run, do not create another one.
        # =====================================================

        old_test_events = [
            event
            for event in existing_events
            if (
                event.title.strip().lower()
                == TEST_TITLE.lower()
            )
        ]

        if old_test_events:

            print()
            print(
                "WARNING: Existing Phase 12 temporary event found."
            )

            for event in old_test_events:
                print(
                    f"{event.event_id}: "
                    f"{event.start.isoformat()} -> "
                    f"{event.end.isoformat()}"
                )

            raise RuntimeError(
                "Temporary Phase 12 event already exists. "
                "Delete it manually before rerunning."
            )

        print(
            "No previous temporary test event found."
        )

        # =====================================================
        # 2. NORMAL CREATION
        # =====================================================

        print()
        print("=" * 70)
        print("TEST 1 - NORMAL CREATION")
        print("=" * 70)

        create_result = create_service.create(
            create_request,
            existing_events=existing_events,
        )

        print(
            f"Status: {create_result.status}"
        )

        print(
            f"Message: {create_result.message}"
        )

        assert create_result.status == "created"

        assert create_result.event is not None

        temporary_event_id = (
            create_result.event.event_id
        )

        print(
            f"Created event ID: {temporary_event_id}"
        )

        assert temporary_event_id

        print(
            "NORMAL CREATION: PASSED"
        )

        # =====================================================
        # 3. VERIFY CREATED EVENT
        # =====================================================

        print()
        print("=" * 70)
        print("TEST 2 - VERIFY CREATED EVENT")
        print("=" * 70)

        events_after_create = (
            search_engine.search_events(
                search_request,
                reference=reference,
            )
        )

        created_event = next(
            (
                event
                for event in events_after_create
                if event.event_id
                == temporary_event_id
            ),
            None,
        )

        assert created_event is not None

        assert (
            created_event.title
            == TEST_TITLE
        )

        assert (
            created_event.start
            == start
        )

        assert (
            created_event.end
            == end
        )

        print(
            f"Found: {created_event.title}"
        )

        print(
            f"{created_event.start.strftime('%H:%M')}"
            f" -> "
            f"{created_event.end.strftime('%H:%M')}"
        )

        print(
            "CREATED EVENT VERIFICATION: PASSED"
        )

        # =====================================================
        # 4. EXACT DUPLICATE
        # =====================================================

        print()
        print("=" * 70)
        print("TEST 3 - EXACT DUPLICATE")
        print("=" * 70)

        duplicate_request = CalendarCreateRequest(
            title=TEST_TITLE,
            start=start,
            end=end,
            description=(
                "Temporary Nexus AI Phase 12 validation event."
            ),
        )

        duplicate_result = (
            create_service.create(
                duplicate_request,
                existing_events=events_after_create,
            )
        )

        print(
            f"Status: {duplicate_result.status}"
        )

        print(
            f"Message: {duplicate_result.message}"
        )

        assert (
            duplicate_result.status
            == "duplicate_blocked"
        )

        assert (
            duplicate_result.existing_duplicate
            is not None
        )

        assert (
            duplicate_result
            .existing_duplicate
            .event_id
            == temporary_event_id
        )

        print(
            "DUPLICATE BLOCKING: PASSED"
        )

        # =====================================================
        # 5. CONFLICT
        #
        # Different title, overlapping time.
        #
        # Existing:
        # 23:00 -> 23:30
        #
        # Proposed:
        # 22:45 -> 23:15
        # =====================================================

        print()
        print("=" * 70)
        print("TEST 4 - OVERLAPPING CONFLICT")
        print("=" * 70)

        conflict_start = tomorrow.replace(
            hour=22,
            minute=45,
            second=0,
            microsecond=0,
        )

        conflict_end = tomorrow.replace(
            hour=23,
            minute=15,
            second=0,
            microsecond=0,
        )

        conflict_request = CalendarCreateRequest(
            title="NEXUS PHASE 12 CONFLICT TEST",
            start=conflict_start,
            end=conflict_end,
        )

        conflict_result = (
            create_service.create(
                conflict_request,
                existing_events=events_after_create,
            )
        )

        print(
            f"Status: {conflict_result.status}"
        )

        print(
            f"Message: {conflict_result.message}"
        )

        assert (
            conflict_result.status
            == "conflict_blocked"
        )

        assert len(
            conflict_result.conflicts
        ) >= 1

        assert any(
            event.event_id
            == temporary_event_id
            for event
            in conflict_result.conflicts
        )

        print(
            "CONFLICT BLOCKING: PASSED"
        )

        # =====================================================
        # 6. TOUCHING RANGE
        #
        # Existing:
        # 23:00 -> 23:30
        #
        # Proposed:
        # 23:30 -> 00:00
        #
        # Boundary touching is NOT a conflict.
        # =====================================================

        print()
        print("=" * 70)
        print("TEST 5 - TOUCHING BOUNDARY")
        print("=" * 70)

        touching_start = end

        touching_end = end + timedelta(
            minutes=30
        )

        touching_request = CalendarCreateRequest(
            title="NEXUS PHASE 12 TOUCHING TEST",
            start=touching_start,
            end=touching_end,
        )

        touching_conflicts = [
            event
            for event in events_after_create
            if (
                event.start < touching_end
                and event.end > touching_start
            )
        ]

        assert not any(
            event.event_id
            == temporary_event_id
            for event in touching_conflicts
        )

        print(
            f"Proposed: "
            f"{touching_start.strftime('%H:%M')}"
            f" -> "
            f"{touching_end.strftime('%H:%M')}"
        )

        print(
            "TOUCHING BOUNDARY: PASSED"
        )

    finally:

        # =====================================================
        # 7. CLEANUP
        # =====================================================

        print()
        print("=" * 70)
        print("CLEANUP")
        print("=" * 70)

        if temporary_event_id is not None:

            print(
                f"Deleting temporary event: "
                f"{temporary_event_id}"
            )

            try:

                client.delete_event(
                    temporary_event_id
                )

                print(
                    "Temporary event deleted."
                )

            except Exception as exc:

                print(
                    "WARNING: Failed to delete "
                    "temporary event."
                )

                print(
                    f"Error: {exc}"
                )

                raise

        else:

            print(
                "No temporary event was created."
            )

    # =========================================================
    # 8. VERIFY CLEANUP
    # =========================================================

    if temporary_event_id is not None:

        print()
        print("=" * 70)
        print("TEST 6 - VERIFY CLEANUP")
        print("=" * 70)

        final_events = (
            search_engine.search_events(
                search_request,
                reference=reference,
            )
        )

        deleted_event = next(
            (
                event
                for event in final_events
                if event.event_id
                == temporary_event_id
            ),
            None,
        )

        assert deleted_event is None

        print(
            "Temporary event no longer exists."
        )

        print(
            "CLEANUP VERIFICATION: PASSED"
        )

    # =========================================================
    # FINAL
    # =========================================================

    print()
    print("=" * 70)
    print("PHASE 12 REAL GOOGLE VALIDATION: PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()