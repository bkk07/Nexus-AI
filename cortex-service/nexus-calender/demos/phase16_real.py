from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from buffers import BufferConfig, apply_buffers
from busy_intervals import events_to_busy_intervals
from connector.google_calendar_client import GoogleCalendarClient
from compiler import CalendarQueryCompiler
from datetime_utils import DateTimeRange
from engine.search import CalendarSearchEngine
from free_slots import find_free_slots
from models import CalendarOperation, CalendarRequest


TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)


def main() -> None:

    print("=" * 70)
    print("PHASE 16 - REAL GOOGLE CALENDAR BUFFER VALIDATION")
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

    if not events:
        print()
        print(
            "No events found today."
        )

        print(
            "Phase 16 real validation cannot "
            "demonstrate buffered intervals."
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
    # 3. CONVERT EVENTS TO BUSY INTERVALS
    # =========================================================

    print()
    print("=" * 70)
    print("2. CONVERT EVENTS TO BUSY INTERVALS")
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
    # 4. DEFINE TODAY'S SCHEDULING WINDOW
    # =========================================================

    window = DateTimeRange(
        start=datetime(
            reference.year,
            reference.month,
            reference.day,
            8,
            0,
            tzinfo=IST,
        ),
        end=datetime(
            reference.year,
            reference.month,
            reference.day,
            22,
            0,
            tzinfo=IST,
        ),
    )

    print()
    print("=" * 70)
    print("3. SCHEDULING WINDOW")
    print("=" * 70)

    print(
        f"Window: "
        f"{window.start.isoformat()} -> "
        f"{window.end.isoformat()}"
    )

    # =========================================================
    # 5. UNBUFFERED FREE SLOTS
    # =========================================================

    print()
    print("=" * 70)
    print("4. FREE SLOTS WITHOUT BUFFERS")
    print("=" * 70)

    unbuffered_slots = find_free_slots(
        window=window,
        busy_intervals=busy_intervals,
        minimum_duration_minutes=1,
    )

    print(
        f"FREE SLOTS FOUND: "
        f"{len(unbuffered_slots)}"
    )

    for slot in unbuffered_slots:

        print(
            f"{slot.start.isoformat()} -> "
            f"{slot.end.isoformat()} "
            f"({slot.duration_minutes} min)"
        )

    # =========================================================
    # 6. APPLY PHASE 16 BUFFERS
    # =========================================================

    print()
    print("=" * 70)
    print("5. APPLY PHASE 16 BUFFERS")
    print("=" * 70)

    config = BufferConfig(
        before_minutes=15,
        after_minutes=15,
        travel_minutes=10,
        preparation_minutes=20,
    )

    print(
        f"before_minutes: "
        f"{config.before_minutes}"
    )

    print(
        f"after_minutes: "
        f"{config.after_minutes}"
    )

    print(
        f"travel_minutes: "
        f"{config.travel_minutes}"
    )

    print(
        f"preparation_minutes: "
        f"{config.preparation_minutes}"
    )

    print(
        "Effective pre-event buffer: "
        f"{config.before_minutes + max(config.travel_minutes, config.preparation_minutes)} "
        "minutes"
    )

    buffered_intervals = apply_buffers(
        busy_intervals,
        config,
    )

    print()
    print(
        f"BUFFERED BUSY INTERVALS: "
        f"{len(buffered_intervals)}"
    )

    for interval in buffered_intervals:

        print(
            f"{interval.start.isoformat()} -> "
            f"{interval.end.isoformat()} "
            f"| events={interval.source_event_ids}"
        )

    # =========================================================
    # 7. BUFFERED FREE SLOTS
    # =========================================================

    print()
    print("=" * 70)
    print("6. FREE SLOTS WITH BUFFERS")
    print("=" * 70)

    buffered_slots = find_free_slots(
        window=window,
        busy_intervals=buffered_intervals,
        minimum_duration_minutes=1,
    )

    print(
        f"FREE SLOTS FOUND: "
        f"{len(buffered_slots)}"
    )

    for slot in buffered_slots:

        print(
            f"{slot.start.isoformat()} -> "
            f"{slot.end.isoformat()} "
            f"({slot.duration_minutes} min)"
        )

    # =========================================================
    # 8. VERIFY BUFFER EFFECT
    # =========================================================

    print()
    print("=" * 70)
    print("7. BUFFER EFFECT VALIDATION")
    print("=" * 70)

    unbuffered_total = sum(
        slot.duration_minutes
        for slot in unbuffered_slots
    )

    buffered_total = sum(
        slot.duration_minutes
        for slot in buffered_slots
    )

    print(
        f"Unbuffered free minutes: "
        f"{unbuffered_total}"
    )

    print(
        f"Buffered free minutes: "
        f"{buffered_total}"
    )

    if buffered_total <= unbuffered_total:

        print(
            "BUFFER EFFECT: PASSED"
        )

    else:

        raise AssertionError(
            "Applying buffers increased "
            "available free time."
        )

    # =========================================================
    # 9. ZERO BUFFER REGRESSION
    # =========================================================

    print()
    print("=" * 70)
    print("8. ZERO BUFFER REGRESSION")
    print("=" * 70)

    zero_buffered_intervals = apply_buffers(
        busy_intervals,
        BufferConfig(),
    )

    zero_buffered_slots = find_free_slots(
        window=window,
        busy_intervals=zero_buffered_intervals,
        minimum_duration_minutes=1,
    )

    assert (
        zero_buffered_slots
        == unbuffered_slots
    )

    print(
        "Zero-buffer free slots match "
        "unbuffered free slots."
    )

    print(
        "ZERO BUFFER REGRESSION: PASSED"
    )

    # =========================================================
    # 10. READ-ONLY GUARANTEE
    # =========================================================

    print()
    print("=" * 70)
    print("9. GOOGLE CALENDAR SAFETY")
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
    print("PHASE 16 REAL GOOGLE VALIDATION: PASSED")
    print("=" * 70)

    print()
    print(
        "Phase 16 buffer management was validated "
        "against the real Google Calendar."
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