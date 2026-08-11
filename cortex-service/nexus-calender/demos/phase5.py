import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from compiler import CalendarQueryCompiler
from connector.fake_calendar_client import (
    FakeCalendarClient,
)
from engine.search import CalendarSearchEngine
from fixtures.fake_calendar_data import (
    FAKE_EVENTS,
)
from models import (
    CalendarOperation,
    CalendarRequest,
)


REFERENCE = datetime(
    2026,
    8,
    11,
    10,
    0,
)


def run_case(
    question: str,
    request: CalendarRequest,
    engine: CalendarSearchEngine,
):

    results = engine.search_events(
        request,
        reference=REFERENCE,
    )

    return {
        "question": question,
        "semantic_request": request.model_dump(
            mode="json"
        ),
        "results": [
            {
                "event_id": event.event_id,
                "title": event.title,
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
                "location": event.location,
                "description": event.description,
            }
            for event in results
        ],
        "count": len(results),
    }


def main():

    client = FakeCalendarClient(
        FAKE_EVENTS
    )

    engine = CalendarSearchEngine(
        client=client,
        compiler=CalendarQueryCompiler(
            default_timezone="Asia/Kolkata",
            default_search_days=30,
        ),
    )

    cases = [
        (
            "Show my events today",
            CalendarRequest(
                operation=CalendarOperation.SEARCH,
                date="today",
            ),
        ),
        (
            "Show my Nexus AI events tomorrow",
            CalendarRequest(
                operation=CalendarOperation.SEARCH,
                query="Nexus AI",
                date="tomorrow",
            ),
        ),
        (
            "Find my DSA events tomorrow",
            CalendarRequest(
                operation=CalendarOperation.SEARCH,
                query="DSA",
                date="tomorrow",
            ),
        ),
        (
            "Show events tomorrow from 18:00 to 22:00",
            CalendarRequest(
                operation=CalendarOperation.SEARCH,
                date="tomorrow",
                start_time="18:00",
                end_time="22:00",
            ),
        ),
        (
            "Show events that do not exist",
            CalendarRequest(
                operation=CalendarOperation.SEARCH,
                query="Does Not Exist",
                date="tomorrow",
            ),
        ),
    ]

    results = [
        run_case(
            question,
            request,
            engine,
        )
        for question, request in cases
    ]

    output = {
        "phase": 5,
        "reference": REFERENCE.isoformat(),
        "results": results,
        "calendar_client": (
            "FakeCalendarClient"
        ),
        "network_call": False,
    }

    print(
        json.dumps(
            output,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()