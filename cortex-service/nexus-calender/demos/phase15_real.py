from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from compiler import CalendarQueryCompiler
from connector.google_calendar_client import GoogleCalendarClient
from engine.delete import CalendarDeleteService
from engine.search import CalendarSearchEngine
from models import (
    CalendarDeleteRequest,
    CalendarOperation,
    CalendarRequest,
    EventSummary,
)

TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)

TEMP_TITLE_ID = "NEXUS PHASE 15 TEMP ID DELETE"
TEMP_TITLE_QUERY = "NEXUS PHASE 15 TEMP QUERY DELETE"


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


def create_temp_event(
    client: GoogleCalendarClient,
    title: str,
    start: datetime,
    end: datetime,
) -> EventSummary:

    event = EventSummary(
        event_id="",
        title=title,
        start=start,
        end=end,
        location=None,
        description=(
            "Temporary event created "
            "for Phase 15 validation."
        ),
    )

    return client.create_event(event)


def main() -> None:

    print("=" * 70)
    print("PHASE 15 - REAL GOOGLE CALENDAR DELETE VALIDATION")
    print("=" * 70)

    reference = datetime.now(IST)

    print()
    print("Reference:")
    print(reference.isoformat())

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

    delete_service = CalendarDeleteService(
        client=client,
    )

    temporary_ids: list[str] = []

    try:

        # =================================================
        # 1. SEARCH TODAY
        # =================================================

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
            f"REAL GOOGLE EVENTS FOUND: "
            f"{len(events)}"
        )

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

        # =================================================
        # 2. CREATE TEMPORARY EVENT FOR ID DELETE
        # =================================================

        print()
        print("=" * 70)
        print("2. CREATE TEMPORARY EVENT")
        print("=" * 70)

        start = today_at(23, 0)
        end = start + timedelta(minutes=30)

        temporary_event = create_temp_event(
            client=client,
            title=TEMP_TITLE_ID,
            start=start,
            end=end,
        )

        temporary_ids.append(
            temporary_event.event_id
        )

        print(
            "Created temporary event:"
        )

        print(
            f"ID: "
            f"{temporary_event.event_id}"
        )

        print(
            f"Time: "
            f"{temporary_event.start.isoformat()} "
            f"-> "
            f"{temporary_event.end.isoformat()}"
        )

        print(
            "TEMPORARY CREATION: PASSED"
        )

        # =================================================
        # 3. DELETE BY EXPLICIT ID
        # =================================================

        print()
        print("=" * 70)
        print("3. DELETE BY EXPLICIT EVENT ID")
        print("=" * 70)

        delete_request = CalendarDeleteRequest(
            operation=CalendarOperation.DELETE,
            event_id=temporary_event.event_id,
        )

        result = delete_service.delete(
            delete_request,
            [temporary_event],
        )

        print(
            f"Status: {result.status}"
        )

        print(
            f"Message: {result.message}"
        )

        assert result.status == "deleted"

        assert result.event is not None

        assert (
            result.event.event_id
            == temporary_event.event_id
        )

        print(
            "EXPLICIT ID DELETE: PASSED"
        )

        # Remove from cleanup list because it
        # has already been deleted successfully.
        temporary_ids.remove(
            temporary_event.event_id
        )

        # =================================================
        # 4. VERIFY EXPLICIT DELETE
        # =================================================

        print()
        print("=" * 70)
        print("4. VERIFY EXPLICIT DELETE")
        print("=" * 70)

        events_after_delete = (
            search_engine.search_events(
                search_request,
                reference=datetime.now(IST),
            )
        )

        found = next(
            (
                event
                for event in events_after_delete
                if event.event_id
                == temporary_event.event_id
            ),
            None,
        )

        assert found is None

        print(
            "Temporary event no longer exists."
        )

        print(
            "EXPLICIT DELETE VERIFICATION: PASSED"
        )

        # =================================================
        # 5. CREATE TEMPORARY EVENT FOR QUERY DELETE
        # =================================================

        print()
        print("=" * 70)
        print("5. CREATE QUERY-DELETE TEST EVENT")
        print("=" * 70)

        start = today_at(23, 0)

        # Use the same late-night slot again because
        # the first temporary event has already gone.
        end = start + timedelta(minutes=30)

        query_event = create_temp_event(
            client=client,
            title=TEMP_TITLE_QUERY,
            start=start,
            end=end,
        )

        temporary_ids.append(
            query_event.event_id
        )

        print(
            f"Created event ID: "
            f"{query_event.event_id}"
        )

        print(
            f"Title: "
            f"{query_event.title}"
        )

        print(
            "QUERY DELETE SETUP: PASSED"
        )

        # =================================================
        # 6. DELETE BY UNIQUE QUERY
        # =================================================

        print()
        print("=" * 70)
        print("6. DELETE BY UNIQUE QUERY")
        print("=" * 70)

        query_delete_request = (
            CalendarDeleteRequest(
                operation=CalendarOperation.DELETE,
                query=TEMP_TITLE_QUERY,
            )
        )

        result = delete_service.delete(
            query_delete_request,
            [query_event],
        )

        print(
            f"Status: {result.status}"
        )

        print(
            f"Message: {result.message}"
        )

        assert result.status == "deleted"

        assert result.event is not None

        assert (
            result.event.event_id
            == query_event.event_id
        )

        print(
            "UNIQUE QUERY DELETE: PASSED"
        )

        temporary_ids.remove(
            query_event.event_id
        )

        # =================================================
        # 7. VERIFY QUERY DELETE
        # =================================================

        print()
        print("=" * 70)
        print("7. VERIFY QUERY DELETE")
        print("=" * 70)

        events_after_query_delete = (
            search_engine.search_events(
                search_request,
                reference=datetime.now(IST),
            )
        )

        found = next(
            (
                event
                for event
                in events_after_query_delete
                if event.event_id
                == query_event.event_id
            ),
            None,
        )

        assert found is None

        print(
            "Query-delete event no longer exists."
        )

        print(
            "QUERY DELETE VERIFICATION: PASSED"
        )

        # =================================================
        # 8. MISSING EVENT ID
        # =================================================

        print()
        print("=" * 70)
        print("8. MISSING EVENT ID")
        print("=" * 70)

        missing_id = (
            "nexus-phase15-event-does-not-exist-"
            "123456789"
        )

        missing_request = CalendarDeleteRequest(
            operation=CalendarOperation.DELETE,
            event_id=missing_id,
        )

        result = delete_service.delete(
            missing_request,
            events_after_query_delete,
        )

        print(
            f"Status: {result.status}"
        )

        assert result.status == "not_found"

        assert result.event is None

        print(
            "MISSING ID DELETE: PASSED"
        )

        # =================================================
        # 9. ZERO RESULT QUERY
        # =================================================

        print()
        print("=" * 70)
        print("9. ZERO RESULT QUERY")
        print("=" * 70)

        nonexistent_query = (
            "NEXUS_PHASE_15_EVENT_DOES_NOT_EXIST"
        )

        zero_request = CalendarDeleteRequest(
            operation=CalendarOperation.DELETE,
            query=nonexistent_query,
        )

        result = delete_service.delete(
            zero_request,
            events_after_query_delete,
        )

        print(
            f"Status: {result.status}"
        )

        assert result.status == "not_found"

        assert result.event is None

        assert result.candidates == []

        print(
            "ZERO RESULT DELETE: PASSED"
        )

        # =================================================
        # 10. REAL AMBIGUITY
        # =================================================

        print()
        print("=" * 70)
        print("10. REAL CALENDAR AMBIGUITY")
        print("=" * 70)

        title_counts: dict[str, int] = {}

        for event in events_after_query_delete:

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
                "No duplicate title exists "
                "in today's real calendar."
            )

            print(
                "AMBIGUITY DELETE: SKIPPED"
            )

        else:

            print(
                f"Ambiguous title found: "
                f"{duplicate_title}"
            )

            ambiguous_request = (
                CalendarDeleteRequest(
                    operation=(
                        CalendarOperation.DELETE
                    ),
                    query=duplicate_title,
                )
            )

            result = delete_service.delete(
                ambiguous_request,
                events_after_query_delete,
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
                "AMBIGUITY DELETE: PASSED"
            )

        # =================================================
        # 11. FINAL
        # =================================================

        print()
        print("=" * 70)
        print(
            "PHASE 15 REAL GOOGLE VALIDATION: PASSED"
        )
        print("=" * 70)

    finally:

        # =================================================
        # CLEANUP ANY LEFTOVER TEMPORARY EVENTS
        # =================================================

        if temporary_ids:

            print()
            print("=" * 70)
            print("FINAL CLEANUP")
            print("=" * 70)

            for event_id in temporary_ids:

                try:

                    print(
                        f"Deleting leftover "
                        f"temporary event: "
                        f"{event_id}"
                    )

                    client.delete_event(
                        event_id
                    )

                    print(
                        "Deleted."
                    )

                except Exception as exc:

                    print(
                        f"Cleanup failed for "
                        f"{event_id}: {exc}"
                    )

            temporary_ids.clear()

            print(
                "FINAL CLEANUP COMPLETED."
            )


if __name__ == "__main__":
    main()