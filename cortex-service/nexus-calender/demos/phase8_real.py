from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from compiler import CalendarQueryCompiler
from engine.busy import BusyIntervalEngine
from engine.search import CalendarSearchEngine
from free_slot_service import FreeSlotService
from models import CalendarOperation, CalendarRequest
from connector.google_calendar_client import GoogleCalendarClient


TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)


def main() -> None:

    print("=" * 70)
    print("PHASE 8 - REAL GOOGLE CALENDAR FREE SLOT VALIDATION")
    print("=" * 70)

    reference = datetime.now(IST)

    print()
    print("Reference:")
    print(reference.isoformat())

    # -----------------------------------------------------
    # REAL GOOGLE CALENDAR
    # -----------------------------------------------------

    client = GoogleCalendarClient(
        calendar_id="primary"
    )

    # -----------------------------------------------------
    # SEARCH ENGINE
    # -----------------------------------------------------

    search_engine = CalendarSearchEngine(
        client=client,
        compiler=CalendarQueryCompiler(
            default_timezone=TIMEZONE,
            default_search_days=30,
        ),
    )

    # -----------------------------------------------------
    # BUSY INTERVAL ENGINE
    # -----------------------------------------------------

    busy_engine = BusyIntervalEngine()

    # -----------------------------------------------------
    # FREE SLOT SERVICE
    # -----------------------------------------------------

    free_slot_service = FreeSlotService(
        busy_engine=busy_engine
    )

    # -----------------------------------------------------
    # SEARCH TOMORROW
    # -----------------------------------------------------

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
            f"{event.start.strftime('%H:%M')}"
            f" -> "
            f"{event.end.strftime('%H:%M')}"
        )

    # -----------------------------------------------------
    # BUILD SCHEDULING WINDOW
    #
    # tomorrow 09:00 -> 22:00
    # -----------------------------------------------------

    compiler = CalendarQueryCompiler(
        default_timezone=TIMEZONE,
    )

    window_request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
        start_time="09:00",
        end_time="22:00",
    )

    query = compiler.compile_search(
        window_request,
        reference=reference,
    )

    window_start = datetime.fromisoformat(
        query["timeMin"]
    )

    window_end = datetime.fromisoformat(
        query["timeMax"]
    )

    from datetime_utils import DateTimeRange

    window = DateTimeRange(
        start=window_start,
        end=window_end,
    )

    # -----------------------------------------------------
    # CHECK ALL FREE SLOTS
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("CHECK 1 - ALL FREE SLOTS")
    print("=" * 70)

    free_slots = free_slot_service.find_free_slots(
        events=events,
        window=window,
        minimum_duration_minutes=1,
    )

    print()

    for slot in free_slots:
        print(
            f"{slot.start.strftime('%H:%M')}"
            f" -> "
            f"{slot.end.strftime('%H:%M')}"
            f" ({slot.duration_minutes} min)"
        )

    # -----------------------------------------------------
    # Expected result for the Phase 6 test calendar:
    #
    # 09:00 -> 12:00 BUSY
    # 14:00 -> 16:00 BUSY
    # 17:00 -> 18:00 BUSY
    # 20:00 -> 22:00 BUSY
    #
    # Therefore:
    #
    # 12:00 -> 14:00 FREE
    # 16:00 -> 17:00 FREE
    # 18:00 -> 20:00 FREE
    # -----------------------------------------------------

    expected_all = [
        ("12:00", "14:00", 120),
        ("16:00", "17:00", 60),
        ("18:00", "20:00", 120),
    ]

    actual_all = [
        (
            slot.start.strftime("%H:%M"),
            slot.end.strftime("%H:%M"),
            slot.duration_minutes,
        )
        for slot in free_slots
    ]

    print()
    print("Expected:")
    for slot in expected_all:
        print(
            f"{slot[0]} -> {slot[1]} "
            f"({slot[2]} min)"
        )

    print()
    print("Actual:")
    for slot in actual_all:
        print(
            f"{slot[0]} -> {slot[1]} "
            f"({slot[2]} min)"
        )

    assert actual_all == expected_all, (
        "Real Google Calendar free slots "
        "do not match expected Phase 6 test calendar."
    )

    # -----------------------------------------------------
    # CHECK MINIMUM 120 MINUTES
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("CHECK 2 - MINIMUM 120 MINUTES")
    print("=" * 70)

    free_slots_120 = (
        free_slot_service.find_free_slots(
            events=events,
            window=window,
            minimum_duration_minutes=120,
        )
    )

    actual_120 = [
        (
            slot.start.strftime("%H:%M"),
            slot.end.strftime("%H:%M"),
            slot.duration_minutes,
        )
        for slot in free_slots_120
    ]

    expected_120 = [
        ("12:00", "14:00", 120),
        ("18:00", "20:00", 120),
    ]

    print()
    print(
        json.dumps(
            actual_120,
            indent=2,
        )
    )

    assert actual_120 == expected_120

    # -----------------------------------------------------
    # FINAL
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("PHASE 8 REAL GOOGLE VALIDATION: PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()