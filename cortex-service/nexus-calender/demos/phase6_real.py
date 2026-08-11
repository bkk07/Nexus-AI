from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from datetime import datetime

from busy_intervals import BusyInterval
from connector.google_calendar_client import GoogleCalendarClient
from engine.busy import BusyIntervalEngine


TEST_PREFIX = "TEST - Busy"
TIMEZONE = "Asia/Kolkata"


def main():

    print("=" * 70)
    print("PHASE 6 - REAL GOOGLE CALENDAR VALIDATION")
    print("=" * 70)

    # -----------------------------------------------------
    # We already know tomorrow's date from our test data.
    # -----------------------------------------------------

    reference = datetime(
        2026,
        8,
        11,
        10,
        0,
    )

    # -----------------------------------------------------
    # Get REAL Google Calendar client.
    # -----------------------------------------------------

    client = GoogleCalendarClient(
        calendar_id="primary"
    )

    # -----------------------------------------------------
    # Search tomorrow's events.
    #
    # We deliberately search without q here so we can
    # inspect all events tomorrow and then select only
    # our controlled TEST - Busy events.
    # -----------------------------------------------------

    query = {
        "timeMin": (
            "2026-08-12T00:00:00+05:30"
        ),
        "timeMax": (
            "2026-08-13T00:00:00+05:30"
        ),
        "singleEvents": True,
        "orderBy": "startTime",
        "timeZone": TIMEZONE,
    }

    all_events = client.search(query)

    # -----------------------------------------------------
    # Keep only our controlled Phase 6 events.
    # -----------------------------------------------------

    test_events = [
        event
        for event in all_events
        if event.title.startswith(TEST_PREFIX)
    ]

    print()
    print(
        f"Found {len(test_events)} Phase 6 test events."
    )

    print()

    for event in test_events:
        print(
            f"{event.title:<20} "
            f"{event.start.strftime('%H:%M')} -> "
            f"{event.end.strftime('%H:%M')}"
        )

    # -----------------------------------------------------
    # Build busy intervals.
    # -----------------------------------------------------

    busy_engine = BusyIntervalEngine()

    busy_intervals = busy_engine.build(
        test_events
    )

    print()
    print("=" * 70)
    print("MERGED BUSY INTERVALS")
    print("=" * 70)

    for interval in busy_intervals:

        print(
            f"{interval.start.strftime('%H:%M')} -> "
            f"{interval.end.strftime('%H:%M')}"
        )

        print(
            "  source_event_ids:"
        )

        for event_id in interval.source_event_ids:
            print(
                f"    - {event_id}"
            )

    # -----------------------------------------------------
    # Expected structure.
    # -----------------------------------------------------

    expected = [
        ("09:00", "12:00"),
        ("14:00", "16:00"),
        ("17:00", "18:00"),
        ("20:00", "22:00"),
    ]

    actual = [
        (
            interval.start.strftime("%H:%M"),
            interval.end.strftime("%H:%M"),
        )
        for interval in busy_intervals
    ]

    print()
    print("=" * 70)
    print("VALIDATION")
    print("=" * 70)

    print("Expected:")
    for start, end in expected:
        print(f"  {start} -> {end}")

    print()
    print("Actual:")
    for start, end in actual:
        print(f"  {start} -> {end}")

    assert len(test_events) == 8, (
        f"Expected 8 test events, "
        f"found {len(test_events)}"
    )

    assert actual == expected, (
        f"Busy interval mismatch.\n"
        f"Expected: {expected}\n"
        f"Actual:   {actual}"
    )

    print()
    print("PHASE 6 REAL GOOGLE VALIDATION: PASSED")


if __name__ == "__main__":
    main()