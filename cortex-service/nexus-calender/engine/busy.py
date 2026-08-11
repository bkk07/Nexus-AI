from __future__ import annotations

from busy_intervals import (
    BusyInterval,
    events_to_busy_intervals,
)
from models import EventSummary


class BusyIntervalEngine:
    """
    Converts calendar events into merged busy intervals.

    This class contains no:
        - Groq calls
        - Google API calls
        - natural-language interpretation

    It operates only on already-normalized EventSummary objects.
    """

    def build(
        self,
        events: list[EventSummary],
    ) -> list[BusyInterval]:
        """
        Convert EventSummary objects into merged busy intervals.
        """

        return events_to_busy_intervals(events)