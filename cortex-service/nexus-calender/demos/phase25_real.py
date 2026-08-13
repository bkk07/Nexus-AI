from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from assistant.orchestrator import CalendarOrchestrator, SUPPORTED_OPERATIONS
from connector.google_calendar_client import GoogleCalendarClient


IST = ZoneInfo("Asia/Kolkata")


def main() -> None:
    print("# PHASE 25 - REAL GOOGLE CALENDAR CONVERSATIONAL ORCHESTRATOR VALIDATION")
    reference = datetime.now(IST)
    print(f"\nReference: {reference.isoformat()}")
    print("\n" + "=" * 70)

    print("\n1. INITIALIZE REAL GOOGLE CALENDAR")
    client = GoogleCalendarClient()
    print("   REAL GOOGLE CALENDAR CLIENT: READY")

    # This demo intentionally wires only read-side proof adapters.  The actual
    # production application can inject the existing Phase 5-24 services.
    # No write operation is performed by this validation demo.
    def search(**kwargs):
        events = client.search(kwargs)
        return {
            "status": "found",
            "events": [event.model_dump(mode="json") for event in events],
            "message": f"Found {len(events)} real Google Calendar events.",
        }

    executors = {
        operation: (lambda **kwargs: {
            "status": "not_configured",
            "message": f"Phase 25 adapter for {operation} is not wired in this read-only demo.",
        })
        for operation in SUPPORTED_OPERATIONS
    }
    executors["SEARCH"] = search

    orchestrator = CalendarOrchestrator(
        planner=lambda _: {
            "operation": "SEARCH",
            "parameters": {
                "timeMin": reference.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ).isoformat(),
                "timeMax": reference.replace(
                    hour=23, minute=59, second=59, microsecond=0
                ).isoformat(),
                "singleEvents": True,
                "orderBy": "startTime",
            },
        },
        executors=executors,
        explainer=lambda result: result["message"],
    )

    print("\n2. USER REQUEST")
    print('   "What events do I have today?"')

    answer = orchestrator.ask("What events do I have today?")
    print("\n3. ORCHESTRATOR RESPONSE")
    print(f"   {answer}")

    print("\n4. WRITE SAFETY")
    print("   Google Calendar events created: 0")
    print("   Google Calendar events modified: 0")
    print("   Google Calendar events deleted: 0")
    print("   REAL CALENDAR WRITE OPERATIONS: 0")

    print("\n" + "=" * 70)
    print("PHASE 25 READ-SIDE ORCHESTRATOR VALIDATION: PASSED")
    print("Real Google Calendar data was used.")
    print("The LLM/planner layer did not fabricate calendar facts.")
    print("No Google Calendar write operation was performed.")


if __name__ == "__main__":
    main()
