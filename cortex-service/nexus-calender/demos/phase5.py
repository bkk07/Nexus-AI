import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from unittest.mock import Mock

from calendar_search import CalendarSearchExecutor


def build_mock_service(response: dict) -> Mock:
    """
    Build a fake Google Calendar service.

    No real Google API request is made.
    """

    service = Mock()

    events_resource = Mock()
    list_request = Mock()

    list_request.execute.return_value = response

    events_resource.list.return_value = list_request
    service.events.return_value = events_resource

    return service


# =========================================================
# FAKE GOOGLE CALENDAR RESPONSE
# =========================================================

GOOGLE_RESPONSE = {
    "items": [
        {
            "id": "event-001",
            "summary": "Nexus AI Meeting",
            "start": {
                "dateTime": "2026-08-12T14:00:00+05:30"
            },
            "end": {
                "dateTime": "2026-08-12T15:00:00+05:30"
            },
            "status": "confirmed",
            "htmlLink": (
                "https://calendar.google.com/event/001"
            ),
        },
        {
            "id": "event-002",
            "summary": "DSA Study",
            "start": {
                "dateTime": "2026-08-12T19:00:00+05:30"
            },
            "end": {
                "dateTime": "2026-08-12T21:00:00+05:30"
            },
            "status": "confirmed",
            "htmlLink": (
                "https://calendar.google.com/event/002"
            ),
        },
        {
            "id": "event-003",
            "summary": "Holiday",
            "start": {
                "date": "2026-08-15"
            },
            "end": {
                "date": "2026-08-16"
            },
            "status": "confirmed",
        },
    ]
}


# =========================================================
# COMPILED QUERY FROM PHASE 4
# =========================================================

QUERY = {
    "q": "Nexus AI",
    "timeMin": (
        "2026-08-12T00:00:00+05:30"
    ),
    "timeMax": (
        "2026-08-13T00:00:00+05:30"
    ),
    "singleEvents": True,
    "orderBy": "startTime",
    "timeZone": "Asia/Kolkata",
}


def main():

    service = build_mock_service(
        GOOGLE_RESPONSE
    )

    executor = CalendarSearchExecutor(
        service=service,
        calendar_id="primary",
    )

    events = executor.search(
        QUERY
    )

    output = {
        "phase": 5,
        "query_sent_to_calendar": QUERY,
        "events_returned": [
            {
                "event_id": event.event_id,
                "summary": event.summary,
                "start": (
                    event.start.isoformat()
                    if event.start
                    else None
                ),
                "end": (
                    event.end.isoformat()
                    if event.end
                    else None
                ),
                "start_is_all_day": (
                    event.start_is_all_day
                ),
                "end_is_all_day": (
                    event.end_is_all_day
                ),
                "status": event.status,
                "html_link": event.html_link,
            }
            for event in events
        ],
        "count": len(events),
    }

    print(
        json.dumps(
            output,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()