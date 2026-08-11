import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from connector.google_calendar_client import GoogleCalendarClient
from engine.search import CalendarSearchEngine
from planner import SearchPlanner


def main():

    question = "Show my Nexus AI events tomorrow"

    reference = datetime.now().astimezone()

    # REAL GROQ
    planner = SearchPlanner()

    request = planner.plan(question)

    # REAL GOOGLE CALENDAR
    client = GoogleCalendarClient(
        calendar_id="primary"
    )

    engine = CalendarSearchEngine(
        client=client
    )

    events = engine.search_events(
        request,
        reference=reference,
    )

    output = {
        "mode": "REAL_GROQ_REAL_GOOGLE_CALENDAR",
        "question": question,

        "groq_extracted": request.model_dump(
            mode="json"
        ),

        "result_count": len(events),

        "events": [
            {
                "event_id": event.event_id,
                "title": event.title,
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
                "location": event.location,
                "description": event.description,
            }
            for event in events
        ],
    }

    print(
        json.dumps(
            output,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()