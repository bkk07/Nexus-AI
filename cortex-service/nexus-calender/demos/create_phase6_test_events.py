from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from connector.google_auth import get_google_calendar_credentials
from googleapiclient.discovery import build


TIMEZONE = "Asia/Kolkata"
CALENDAR_ID = "primary"


TEST_EVENTS = [
    ("TEST - Busy A", "09:00", "10:00"),
    ("TEST - Busy B", "09:30", "11:00"),
    ("TEST - Busy C", "11:00", "12:00"),
    ("TEST - Busy D", "14:00", "15:00"),
    ("TEST - Busy E", "14:30", "16:00"),
    ("TEST - Busy F", "17:00", "17:30"),
    ("TEST - Busy G", "17:00", "18:00"),
    ("TEST - Busy H", "20:00", "22:00"),
]


def make_datetime(
    date: str,
    time: str,
) -> datetime:
    return datetime.fromisoformat(
        f"{date}T{time}:00"
    )


def create_event(
    service,
    title: str,
    start_time: str,
    end_time: str,
):
    date = "2026-08-12"

    start = make_datetime(
        date,
        start_time,
    )

    end = make_datetime(
        date,
        end_time,
    )

    event = {
        "summary": title,
        "description": (
            "Nexus Calendar Phase 6 test event. "
            "Safe to delete."
        ),
        "start": {
            "dateTime": start.isoformat(),
            "timeZone": TIMEZONE,
        },
        "end": {
            "dateTime": end.isoformat(),
            "timeZone": TIMEZONE,
        },
    }

    return (
        service
        .events()
        .insert(
            calendarId=CALENDAR_ID,
            body=event,
        )
        .execute()
    )


def main():

    credentials = get_google_calendar_credentials()

    service = build(
        "calendar",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    print("=" * 70)
    print("CREATING PHASE 6 TEST EVENTS")
    print("=" * 70)

    for title, start, end in TEST_EVENTS:

        event = create_event(
            service,
            title,
            start,
            end,
        )

        print(
            f"{title:<20} "
            f"{start} -> {end}"
        )

        print(
            f"  ID: {event['id']}"
        )

    print()
    print("Created:", len(TEST_EVENTS), "test events")
    print("Date: 2026-08-12")
    print("Timezone:", TIMEZONE)


if __name__ == "__main__":
    main()