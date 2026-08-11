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
from conflicts import find_conflicts
from connector.calendar_client import CalendarClient
from connector.google_calendar_client import GoogleCalendarClient
from datetime_utils import DateTimeRange
from engine.search import CalendarSearchEngine
from models import CalendarOperation, CalendarRequest


TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)


def main() -> None:

    print("=" * 70)
    print("PHASE 11 - REAL GOOGLE CALENDAR CONFLICT VALIDATION")
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

    # =========================================================
    # SEARCH TOMORROW
    # =========================================================

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
        start_time="09:00",
        end_time="22:00",
    )

    events = search_engine.search_events(
        request,
        reference=reference,
    )

    print()
    print(
        f"REAL GOOGLE EVENTS FOUND: {len(events)}"
    )

    for event in events:
        print(
            f"{event.title}: "
            f"{event.start.strftime('%H:%M')} -> "
            f"{event.end.strftime('%H:%M')}"
        )

    # =========================================================
    # PROPOSED RANGE
    #
    # 10:30 -> 15:30
    # =========================================================

    query = compiler.compile_search(
        request,
        reference=reference,
    )

    proposed_range = DateTimeRange(
        start=datetime.fromisoformat(
            query["timeMin"]
        ).replace(
            hour=10,
            minute=30,
        ),
        end=datetime.fromisoformat(
            query["timeMin"]
        ).replace(
            hour=15,
            minute=30,
        ),
    )

    print()
    print("=" * 70)
    print("PROPOSED RANGE")
    print("=" * 70)

    print(
        f"{proposed_range.start.strftime('%H:%M')}"
        f" -> "
        f"{proposed_range.end.strftime('%H:%M')}"
    )

    # =========================================================
    # FIND INDIVIDUAL CONFLICTS
    # =========================================================

    conflicts = find_conflicts(
        proposed_range,
        events,
    )

    print()
    print("=" * 70)
    print("CONFLICTS")
    print("=" * 70)

    if not conflicts:
        print("No conflicts found.")
    else:
        for event in conflicts:
            print(
                f"{event.title}: "
                f"{event.start.strftime('%H:%M')}"
                f" -> "
                f"{event.end.strftime('%H:%M')}"
            )

    # =========================================================
    # EXPECTED CONFLICTS
    #
    # With the Phase 6 test calendar:
    #
    # 09:30 -> 11:00
    # 11:00 -> 12:00
    # 14:00 -> 15:00
    # 14:30 -> 16:00
    #
    # These must remain individual events.
    # =========================================================

    expected_event_ranges = {
        (
            "09:30",
            "11:00",
        ),
        (
            "11:00",
            "12:00",
        ),
        (
            "14:00",
            "15:00",
        ),
        (
            "14:30",
            "16:00",
        ),
    }

    actual_event_ranges = {
        (
            event.start.strftime("%H:%M"),
            event.end.strftime("%H:%M"),
        )
        for event in conflicts
    }

    print()
    print("Expected conflicts:")

    for start, end in sorted(
        expected_event_ranges
    ):
        print(
            f"{start} -> {end}"
        )

    print()
    print("Actual conflicts:")

    for start, end in sorted(
        actual_event_ranges
    ):
        print(
            f"{start} -> {end}"
        )

    # =========================================================
    # VALIDATION
    # =========================================================

    assert actual_event_ranges == expected_event_ranges

    assert len(conflicts) == 4

    # Make sure conflicts were NOT merged.
    assert not (
        len(conflicts) == 2
        and actual_event_ranges == {
            ("09:30", "12:00"),
            ("14:00", "16:00"),
        }
    )

    # =========================================================
    # BOUNDARY TEST
    #
    # 12:00 -> 14:00 touches the existing events:
    #
    # 11:00 -> 12:00
    # 14:00 -> 15:00
    #
    # Therefore it must have ZERO conflicts.
    # =========================================================

    boundary_range = DateTimeRange(
        start=proposed_range.start.replace(
            hour=12,
            minute=0,
        ),
        end=proposed_range.start.replace(
            hour=14,
            minute=0,
        ),
    )

    boundary_conflicts = find_conflicts(
        boundary_range,
        events,
    )

    print()
    print("=" * 70)
    print("BOUNDARY TEST")
    print("=" * 70)

    print("12:00 -> 14:00")

    print(
        f"Conflicts found: "
        f"{len(boundary_conflicts)}"
    )

    assert boundary_conflicts == []

    print("Boundary test: PASSED")

    # =========================================================
    # FINAL
    # =========================================================

    print()
    print("=" * 70)
    print("PHASE 11 REAL GOOGLE VALIDATION: PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()