from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from availability_service import AvailabilityService
from engine.busy import BusyIntervalEngine
from compiler import CalendarQueryCompiler
from connector.google_calendar_client import GoogleCalendarClient
from engine.search import CalendarSearchEngine
from models import CalendarOperation, CalendarRequest


TIMEZONE = "Asia/Kolkata"

IST = ZoneInfo(TIMEZONE)


def run_check(
    *,
    search_engine: CalendarSearchEngine,
    busy_engine: BusyIntervalEngine,
    availability_service: AvailabilityService,
    reference: datetime,
    start_time: str,
    end_time: str,
):
    # -----------------------------------------------------
    # First retrieve REAL Google Calendar events.
    # -----------------------------------------------------

    search_request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
    )

    events = search_engine.search_events(
        search_request,
        reference=reference,
    )

    # -----------------------------------------------------
    # Convert real events into merged busy intervals.
    # -----------------------------------------------------

    busy_intervals = busy_engine.build(
        events
    )

    # -----------------------------------------------------
    # Build availability request.
    # -----------------------------------------------------

    availability_request = CalendarRequest(
        operation=CalendarOperation.CHECK_AVAILABILITY,
        date="tomorrow",
        start_time=start_time,
        end_time=end_time,
    )

    # -----------------------------------------------------
    # Check availability.
    # -----------------------------------------------------

    result = availability_service.check(
        availability_request,
        busy_intervals,
        reference=reference,
    )

    return events, busy_intervals, result


def serialize_result(
    result,
):
    return {
        "available": result.available,
        "requested_start": result.requested_range.start.isoformat(),
        "requested_end": result.requested_range.end.isoformat(),
        "conflicts": [
            {
                "start": interval.start.isoformat(),
                "end": interval.end.isoformat(),
                "source_event_ids": interval.source_event_ids,
            }
            for interval in result.conflicts
        ],
    }


def main():

    print("=" * 70)
    print("PHASE 7 - REAL GOOGLE CALENDAR AVAILABILITY")
    print("=" * 70)

    # -----------------------------------------------------
    # Reference time.
    # -----------------------------------------------------

    reference = datetime.now(IST)

    print()
    print(
        "Reference:",
        reference.isoformat(),
    )

    # -----------------------------------------------------
    # REAL Google Calendar client.
    # -----------------------------------------------------

    client = GoogleCalendarClient(
        calendar_id="primary"
    )

    # -----------------------------------------------------
    # Search pipeline.
    # -----------------------------------------------------

    search_engine = CalendarSearchEngine(
        client=client,
        compiler=CalendarQueryCompiler(
            default_timezone=TIMEZONE,
            default_search_days=30,
        ),
    )

    busy_engine = BusyIntervalEngine()

    availability_service = AvailabilityService(
        default_timezone=TIMEZONE
    )

    # =====================================================
    # CHECK 1
    # =====================================================

    print()
    print("=" * 70)
    print("CHECK 1: TOMORROW 19:00 -> 21:00")
    print("=" * 70)

    events, busy_intervals, result = run_check(
        search_engine=search_engine,
        busy_engine=busy_engine,
        availability_service=availability_service,
        reference=reference,
        start_time="19:00",
        end_time="21:00",
    )

    print()
    print(
        f"Google events found: {len(events)}"
    )

    print()
    print("Merged busy intervals:")

    for interval in busy_intervals:
        print(
            f"  {interval.start.strftime('%H:%M')}"
            f" -> "
            f"{interval.end.strftime('%H:%M')}"
        )

    print()
    print(
        json.dumps(
            serialize_result(result),
            indent=2,
        )
    )

    assert result.available is False, (
        "Expected tomorrow 19:00-21:00 "
        "to be BUSY because the test calendar "
        "contains TEST - Busy H from 20:00-22:00."
    )

    assert len(result.conflicts) > 0

    # =====================================================
    # CHECK 2
    # =====================================================

    print()
    print("=" * 70)
    print("CHECK 2: TOMORROW 18:00 -> 19:00")
    print("=" * 70)

    _, _, result_free = run_check(
        search_engine=search_engine,
        busy_engine=busy_engine,
        availability_service=availability_service,
        reference=reference,
        start_time="18:00",
        end_time="19:00",
    )

    print()
    print(
        json.dumps(
            serialize_result(result_free),
            indent=2,
        )
    )

    assert result_free.available is True, (
        "Expected tomorrow 18:00-19:00 "
        "to be FREE because the 17:00-18:00 "
        "busy interval only touches the boundary."
    )

    assert result_free.conflicts == []

    # =====================================================
    # FINAL
    # =====================================================

    print()
    print("=" * 70)
    print("PHASE 7 REAL GOOGLE VALIDATION: PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()