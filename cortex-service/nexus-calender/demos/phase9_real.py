from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime
from zoneinfo import ZoneInfo

from compiler import CalendarQueryCompiler
from connector.calendar_client import CalendarClient
from connector.google_calendar_client import GoogleCalendarClient
from datetime_utils import DateTimeRange
from engine.busy import BusyIntervalEngine
from engine.search import CalendarSearchEngine
from free_slot_service import FreeSlotService
from models import CalendarOperation, CalendarRequest
from next_slot import NextSlotService


TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)


def main() -> None:

    print("=" * 70)
    print("PHASE 9 - REAL GOOGLE CALENDAR NEXT FREE SLOT VALIDATION")
    print("=" * 70)

    reference = datetime.now(IST)

    print()
    print("Reference:")
    print(reference.isoformat())

    # ---------------------------------------------------------
    # REAL GOOGLE CALENDAR CLIENT
    # ---------------------------------------------------------

    client: CalendarClient = GoogleCalendarClient(
        calendar_id="primary",
    )

    # ---------------------------------------------------------
    # SEARCH ENGINE
    # ---------------------------------------------------------

    compiler = CalendarQueryCompiler(
        default_timezone=TIMEZONE,
        default_search_days=30,
    )

    search_engine = CalendarSearchEngine(
        client=client,
        compiler=compiler,
    )

    # ---------------------------------------------------------
    # SEARCH TOMORROW
    # ---------------------------------------------------------

    search_request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
    )

    events = search_engine.search_events(
        search_request,
        reference=reference,
    )

    print()
    print(
        f"REAL GOOGLE EVENTS FOUND: {len(events)}"
    )

    for event in events:
        print(
            f"{event.title}: "
            f"{event.start.isoformat()} -> "
            f"{event.end.isoformat()}"
        )

    # ---------------------------------------------------------
    # CREATE NEXT SLOT SERVICE
    # ---------------------------------------------------------

    busy_engine = BusyIntervalEngine()

    free_slot_service = FreeSlotService(
        busy_engine=busy_engine,
    )

    next_slot_service = NextSlotService(
        free_slot_service=free_slot_service,
    )

    # ---------------------------------------------------------
    # TOMORROW 09:00
    # ---------------------------------------------------------

    tomorrow_request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
        start_time="09:00",
        end_time="22:00",
    )

    tomorrow_query = compiler.compile_search(
        tomorrow_request,
        reference=reference,
    )

    window_start = datetime.fromisoformat(
        tomorrow_query["timeMin"]
    )

    window_end = datetime.fromisoformat(
        tomorrow_query["timeMax"]
    )

    window = DateTimeRange(
        start=window_start,
        end=window_end,
    )

    # ---------------------------------------------------------
    # DISPLAY BUSY INTERVALS
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("BUSY INTERVALS")
    print("=" * 70)

    busy_intervals = busy_engine.build(events)

    for interval in busy_intervals:
        print(
            f"{interval.start.strftime('%H:%M')}"
            f" -> "
            f"{interval.end.strftime('%H:%M')}"
        )

    # ---------------------------------------------------------
    # FIND NEXT 2-HOUR SLOT
    #
    # We use the same real events and scheduling window.
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("CHECK 1 - NEXT 2-HOUR SLOT")
    print("=" * 70)

    # Filter events to the requested scheduling window.
    window_events = [
        event
        for event in events
        if event.start < window.end
        and event.end > window.start
    ]

    result = next_slot_service.find_next_free_slot(
        events=window_events,
        earliest_start=window.start,
        duration_minutes=120,
        horizon_days=1,
    )

    if result is None:
        print()
        print("No 2-hour free slot found.")
    else:
        print()
        print(
            f"NEXT FREE SLOT: "
            f"{result.start.strftime('%H:%M')}"
            f" -> "
            f"{result.end.strftime('%H:%M')}"
        )

        print(
            f"Duration: "
            f"{result.duration_minutes} minutes"
        )

    # ---------------------------------------------------------
    # EXPECTATION FOR YOUR PHASE 6 TEST CALENDAR
    #
    # Busy:
    #
    # 09:00 -> 12:00
    # 14:00 -> 16:00
    # 17:00 -> 18:00
    # 20:00 -> 22:00
    #
    # Therefore the next 2-hour slot from 09:00 is:
    #
    # 12:00 -> 14:00
    # ---------------------------------------------------------

    expected_start = "12:00"
    expected_end = "14:00"

    if result is None:
        raise AssertionError(
            "Expected a 2-hour free slot, "
            "but none was found."
        )

    actual_start = result.start.strftime(
        "%H:%M"
    )

    actual_end = result.end.strftime(
        "%H:%M"
    )

    print()
    print("Expected:")
    print(
        f"{expected_start} -> "
        f"{expected_end}"
    )

    print()
    print("Actual:")
    print(
        f"{actual_start} -> "
        f"{actual_end}"
    )

    assert actual_start == expected_start
    assert actual_end == expected_end

    assert result.duration_minutes >= 120

    # ---------------------------------------------------------
    # CHECK 2 - NEXT 3-HOUR SLOT
    #
    # No 3-hour slot exists today in the Phase 6 test
    # calendar, so this should return None when horizon_days=1.
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("CHECK 2 - NEXT 3-HOUR SLOT")
    print("=" * 70)

    result_3h = next_slot_service.find_next_free_slot(
        events=window_events,
        earliest_start=window.start,
        duration_minutes=180,
        horizon_days=1,
    )

    if result_3h is None:
        print()
        print(
            "No 3-hour free slot found "
            "within tomorrow's 09:00 -> 22:00 window."
        )
    else:
        print()
        print(
            f"3-HOUR SLOT: "
            f"{result_3h.start.strftime('%H:%M')}"
            f" -> "
            f"{result_3h.end.strftime('%H:%M')}"
        )

    # There is no 3-hour free interval in the Phase 6 calendar.
    assert result_3h is None

    # ---------------------------------------------------------
    # FINAL
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("PHASE 9 REAL GOOGLE VALIDATION: PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()