from __future__ import annotations


import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, time
from zoneinfo import ZoneInfo

from best_slot import BestSlotService
from compiler import CalendarQueryCompiler
from connector.calendar_client import CalendarClient
from connector.google_calendar_client import GoogleCalendarClient
from datetime_utils import DateTimeRange
from engine.busy import BusyIntervalEngine
from engine.search import CalendarSearchEngine
from free_slot_service import FreeSlotService
from models import CalendarOperation, CalendarRequest


TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)


def main() -> None:

    print("=" * 70)
    print("PHASE 10 - REAL GOOGLE CALENDAR BEST SLOT VALIDATION")
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
    print(f"REAL GOOGLE EVENTS FOUND: {len(events)}")

    for event in events:
        print(
            f"{event.title}: "
            f"{event.start.strftime('%H:%M')} -> "
            f"{event.end.strftime('%H:%M')}"
        )

    # =========================================================
    # BUILD SCHEDULING WINDOW
    # =========================================================

    query = compiler.compile_search(
        request,
        reference=reference,
    )

    window = DateTimeRange(
        start=datetime.fromisoformat(
            query["timeMin"]
        ),
        end=datetime.fromisoformat(
            query["timeMax"]
        ),
    )

    # =========================================================
    # FREE SLOT PIPELINE
    # =========================================================

    busy_engine = BusyIntervalEngine()

    free_service = FreeSlotService(
        busy_engine=busy_engine,
    )

    candidates = free_service.find_free_slots(
        events=events,
        window=window,
        minimum_duration_minutes=120,
    )

    print()
    print("=" * 70)
    print("FREE SLOT CANDIDATES")
    print("=" * 70)

    for candidate in candidates:
        print(
            f"{candidate.start.strftime('%H:%M')} -> "
            f"{candidate.end.strftime('%H:%M')} "
            f"({candidate.duration_minutes} min)"
        )

    # =========================================================
    # BEST SLOT RANKING
    # =========================================================

    best_service = BestSlotService()

    ranked = best_service.rank_slots(
        slots=candidates,
        requested_duration_minutes=120,
        preferred_start=time(18, 0),
    )

    print()
    print("=" * 70)
    print("RANKED SLOTS")
    print("=" * 70)

    for index, item in enumerate(
        ranked,
        start=1,
    ):
        print()
        print(
            f"#{index} "
            f"{item.slot.start.strftime('%H:%M')} -> "
            f"{item.slot.end.strftime('%H:%M')}"
        )

        print(
            f"Duration: "
            f"{item.slot.duration_minutes} minutes"
        )

        print(
            f"Score: "
            f"{item.score:.6f}"
        )

        print("Reasons:")

        for reason in item.reasons:
            print(f"  - {reason}")

    # =========================================================
    # BEST SLOT
    # =========================================================

    result = best_service.find_best_slot(
        slots=candidates,
        requested_duration_minutes=120,
        preferred_start=time(18, 0),
    )

    print()
    print("=" * 70)
    print("BEST SLOT")
    print("=" * 70)

    if result is None:
        raise AssertionError(
            "Expected at least one valid 2-hour slot."
        )

    print(
        f"{result.slot.start.strftime('%H:%M')} -> "
        f"{result.slot.end.strftime('%H:%M')}"
    )

    print(
        f"Duration: "
        f"{result.slot.duration_minutes} minutes"
    )

    print(
        f"Score: "
        f"{result.score:.6f}"
    )

    # =========================================================
    # DETERMINISM CHECK
    # =========================================================

    second_result = best_service.find_best_slot(
        slots=candidates,
        requested_duration_minutes=120,
        preferred_start=time(18, 0),
    )

    assert second_result is not None

    assert (
        result.slot.start
        == second_result.slot.start
    )

    assert (
        result.slot.end
        == second_result.slot.end
    )

    assert (
        result.score
        == second_result.score
    )

    print()
    print("Determinism check: PASSED")

    # =========================================================
    # FINAL
    # =========================================================

    print()
    print("=" * 70)
    print("PHASE 10 REAL GOOGLE VALIDATION: PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()