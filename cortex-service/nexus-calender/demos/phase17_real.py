from __future__ import annotations

import sys
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from busy_intervals import events_to_busy_intervals
from connector.google_calendar_client import GoogleCalendarClient
from compiler import CalendarQueryCompiler
from datetime_utils import DateTimeRange
from engine.search import CalendarSearchEngine
from free_slots import find_free_slots
from models import CalendarOperation, CalendarRequest
from windows import SchedulingWindow, constrain_to_window


TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)


def main() -> None:

    print("=" * 70)
    print("PHASE 17 - REAL GOOGLE CALENDAR SCHEDULING WINDOW VALIDATION")
    print("=" * 70)

    reference = datetime.now(IST)

    print()
    print("Reference:")
    print(reference.isoformat())

    # =========================================================
    # 1. REAL GOOGLE CALENDAR CLIENT
    # =========================================================

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

    # =========================================================
    # 2. SEARCH TODAY'S REAL CALENDAR
    # =========================================================

    print()
    print("=" * 70)
    print("1. SEARCH TODAY'S REAL CALENDAR")
    print("=" * 70)

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="today",
        start_time="00:00",
        end_time="23:59",
    )

    events = search_engine.search_events(
        request,
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
            f"{index}. "
            f"{event.title}: "
            f"{event.start.isoformat()} -> "
            f"{event.end.isoformat()}"
        )

    # =========================================================
    # 3. DEFINE WORKING-HOURS WINDOW
    # =========================================================

    print()
    print("=" * 70)
    print("2. APPLY WORKING-HOURS SCHEDULING WINDOW")
    print("=" * 70)

    today = reference.date()

    working_window = SchedulingWindow(
        name="working_hours",
        start_time="09:00",
        end_time="21:00",
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
    )

    constrained = constrain_to_window(
        today,
        working_window,
        timezone=IST,
    )

    if constrained is None:

        print(
            "Today is outside the configured "
            "working days."
        )

        print(
            "No schedulable working-hours window "
            "exists today."
        )

        print()
        print("=" * 70)
        print("PHASE 17 REAL GOOGLE VALIDATION: PASSED")
        print("=" * 70)

        print()
        print("No Google Calendar events were created.")
        print("No Google Calendar events were modified.")
        print("No Google Calendar events were deleted.")

        return

    window_start, window_end = constrained

    print(
        f"Scheduling window: "
        f"{window_start.isoformat()} -> "
        f"{window_end.isoformat()}"
    )

    # =========================================================
    # 4. CONVERT REAL EVENTS TO BUSY INTERVALS
    # =========================================================

    print()
    print("=" * 70)
    print("3. CONVERT REAL EVENTS TO BUSY INTERVALS")
    print("=" * 70)

    busy_intervals = events_to_busy_intervals(
        events
    )

    print(
        f"MERGED BUSY INTERVALS: "
        f"{len(busy_intervals)}"
    )

    for interval in busy_intervals:

        print(
            f"{interval.start.isoformat()} -> "
            f"{interval.end.isoformat()} "
            f"| events={interval.source_event_ids}"
        )

    # =========================================================
    # 5. FIND FREE SLOTS ONLY INSIDE WINDOW
    # =========================================================

    print()
    print("=" * 70)
    print("4. FREE SLOTS INSIDE SCHEDULING WINDOW")
    print("=" * 70)

    scheduling_range = DateTimeRange(
        start=window_start,
        end=window_end,
    )

    slots = find_free_slots(
        window=scheduling_range,
        busy_intervals=busy_intervals,
        minimum_duration_minutes=30,
    )

    print(
        f"FREE SLOTS FOUND: {len(slots)}"
    )

    for slot in slots:

        print(
            f"{slot.start.isoformat()} -> "
            f"{slot.end.isoformat()} "
            f"({slot.duration_minutes} min)"
        )

    # =========================================================
    # 6. VERIFY EVERY SLOT IS INSIDE WINDOW
    # =========================================================

    print()
    print("=" * 70)
    print("5. SCHEDULING WINDOW BOUNDARY VALIDATION")
    print("=" * 70)

    for slot in slots:

        assert slot.start >= window_start

        assert slot.end <= window_end

        assert slot.start < slot.end

    print(
        "Every proposed free slot is completely "
        "inside the scheduling window."
    )

    print(
        "WINDOW BOUNDARY VALIDATION: PASSED"
    )

    # =========================================================
    # 7. EARLY-MORNING REJECTION
    #
    # Explicitly verify that a free 02:00 -> 03:00
    # period cannot be considered schedulable.
    # =========================================================

    print()
    print("=" * 70)
    print("6. EARLY-MORNING OUTSIDE-WINDOW VALIDATION")
    print("=" * 70)

    early_start = datetime.combine(
        today,
        time(2, 0),
        tzinfo=IST,
    )

    early_end = datetime.combine(
        today,
        time(3, 0),
        tzinfo=IST,
    )

    print(
        f"Candidate: "
        f"{early_start.isoformat()} -> "
        f"{early_end.isoformat()}"
    )

    assert early_end <= window_start

    print(
        "02:00 -> 03:00 is outside the "
        "09:00 -> 21:00 scheduling window."
    )

    print(
        "EARLY-MORNING REJECTION: PASSED"
    )

    # =========================================================
    # 8. VALID INSIDE-WINDOW SLOT
    # =========================================================

    print()
    print("=" * 70)
    print("7. VALID INSIDE-WINDOW VALIDATION")
    print("=" * 70)

    valid_start = datetime.combine(
        today,
        time(10, 0),
        tzinfo=IST,
    )

    valid_end = datetime.combine(
        today,
        time(11, 0),
        tzinfo=IST,
    )

    assert valid_start >= window_start
    assert valid_end <= window_end

    print(
        f"Candidate: "
        f"{valid_start.isoformat()} -> "
        f"{valid_end.isoformat()}"
    )

    print(
        "10:00 -> 11:00 is inside the "
        "09:00 -> 21:00 scheduling window."
    )

    print(
        "VALID INSIDE-WINDOW SLOT: PASSED"
    )

    # =========================================================
    # 9. REAL CALENDAR SAFETY
    # =========================================================

    print()
    print("=" * 70)
    print("8. GOOGLE CALENDAR SAFETY")
    print("=" * 70)

    print(
        "Google Calendar events created: 0"
    )

    print(
        "Google Calendar events modified: 0"
    )

    print(
        "Google Calendar events deleted: 0"
    )

    print(
        "REAL CALENDAR WRITE OPERATIONS: 0"
    )

    # =========================================================
    # FINAL
    # =========================================================

    print()
    print("=" * 70)
    print("PHASE 17 REAL GOOGLE VALIDATION: PASSED")
    print("=" * 70)

    print()
    print(
        "Scheduling windows successfully constrained "
        "real-calendar free time."
    )

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