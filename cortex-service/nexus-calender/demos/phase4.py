import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from compiler import CalendarQueryCompiler
from models import CalendarOperation, CalendarRequest


REFERENCE = datetime(
    2026,
    8,
    11,
    10,
    0,
)


compiler = CalendarQueryCompiler(
    default_timezone="Asia/Kolkata",
    default_search_days=30,
)


TEST_CASES = [
    CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="Nexus AI",
        date="tomorrow",
    ),

    CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="today",
    ),

    CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="DSA",
        date="this week",
    ),

    CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="Nexus AI",
        date="tomorrow",
        start_time="2 PM",
        end_time="5 PM",
    ),

    CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="Lunch",
        date="today",
        start_time="12 PM",
        end_time="1 AM",
    ),

    CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="Nexus AI",
    ),

    CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="DSA",
        date="last 7 days",
    ),
]


def main():
    results = []

    for request in TEST_CASES:

        compiled = compiler.compile_search(
            request,
            reference=REFERENCE,
        )

        results.append(
            {
                "semantic_request": request.model_dump(
                    mode="json"
                ),
                "google_calendar_query": compiled,
            }
        )

    print(
        json.dumps(
            results,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()