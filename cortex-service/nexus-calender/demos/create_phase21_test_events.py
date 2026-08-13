from __future__ import annotations

import sys

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from connector.google_calendar_client import (
    GoogleCalendarClient,
)
from models import EventSummary


IST = ZoneInfo("Asia/Kolkata")


TEST_EVENTS = [
    (
        "PHASE 21 TEST - Busy A",
        9,
        10,
    ),
    (
        "PHASE 21 TEST - Busy B",
        13,
        14,
    ),
    (
        "PHASE 21 TEST - Busy C",
        16,
        17,
    ),
    (
        "PHASE 21 TEST - Busy D",
        20,
        21,
    ),
]


def make_event(
    title: str,
    start_hour: int,
    end_hour: int,
) -> EventSummary:

    start = datetime(
        2026,
        8,
        14,
        start_hour,
        0,
        tzinfo=IST,
    )

    end = datetime(
        2026,
        8,
        14,
        end_hour,
        0,
        tzinfo=IST,
    )

    return EventSummary(
        event_id="temporary",
        title=title,
        start=start,
        end=end,
        location=None,
        description=(
            "Temporary Phase 21 validation event. "
            "Safe to delete after testing."
        ),
    )


def main() -> None:

    print()
    print(
        "# CREATE PHASE 21 REAL CALENDAR TEST EVENTS"
    )

    print()

    client = GoogleCalendarClient()

    created = []

    for title, start_hour, end_hour in TEST_EVENTS:

        event = make_event(
            title,
            start_hour,
            end_hour,
        )

        created_event = client.create_event(
            event,
        )

        created.append(
            created_event
        )

        print(
            f"CREATED: {created_event.title}"
        )

        print(
            f"  ID: {created_event.event_id}"
        )

        print(
            f"  {created_event.start.isoformat()}"
            f" -> "
            f"{created_event.end.isoformat()}"
        )

        print()

    print("=" * 70)

    print(
        f"TOTAL CREATED: {len(created)}"
    )

    print()
    print(
        "These events are intentionally temporary "
        "Phase 21 validation data."
    )

    print(
        "Run phase21_real.py after this."
    )

    print(
        "The event IDs above can be used for cleanup."
    )


if __name__ == "__main__":
    main()