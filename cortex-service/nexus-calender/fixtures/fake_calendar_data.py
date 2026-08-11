from datetime import datetime

from models import EventSummary


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


FAKE_EVENTS = [
    EventSummary(
        event_id="evt-nexus-1",
        title="Nexus AI Meeting",
        start=dt(
            "2026-08-12T10:00:00+05:30"
        ),
        end=dt(
            "2026-08-12T11:00:00+05:30"
        ),
        location="Nexus Lab",
        description="Nexus AI architecture discussion",
    ),

    EventSummary(
        event_id="evt-dsa-1",
        title="DSA Study",
        start=dt(
            "2026-08-12T19:00:00+05:30"
        ),
        end=dt(
            "2026-08-12T21:00:00+05:30"
        ),
        location="Library",
        description="Graph algorithms and dynamic programming",
    ),

    EventSummary(
        event_id="evt-project-1",
        title="Nexus Project Work",
        start=dt(
            "2026-08-13T14:00:00+05:30"
        ),
        end=dt(
            "2026-08-13T16:00:00+05:30"
        ),
        location="Home",
        description="Backend implementation",
    ),

    EventSummary(
        event_id="evt-meeting-1",
        title="Team Meeting",
        start=dt(
            "2026-08-11T15:00:00+05:30"
        ),
        end=dt(
            "2026-08-11T16:00:00+05:30"
        ),
        location="Online",
        description="Weekly team sync",
    ),

    # Recurring-style fixture instances.
    EventSummary(
        event_id="evt-recurring-1",
        title="Daily Standup",
        start=dt(
            "2026-08-11T09:00:00+05:30"
        ),
        end=dt(
            "2026-08-11T09:15:00+05:30"
        ),
    ),

    EventSummary(
        event_id="evt-recurring-2",
        title="Daily Standup",
        start=dt(
            "2026-08-12T09:00:00+05:30"
        ),
        end=dt(
            "2026-08-12T09:15:00+05:30"
        ),
    ),

    EventSummary(
        event_id="evt-recurring-3",
        title="Daily Standup",
        start=dt(
            "2026-08-13T09:00:00+05:30"
        ),
        end=dt(
            "2026-08-13T09:15:00+05:30"
        ),
    ),
]