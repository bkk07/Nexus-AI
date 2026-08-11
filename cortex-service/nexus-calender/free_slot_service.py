from __future__ import annotations

from busy_intervals import BusyInterval
from engine.busy import BusyIntervalEngine
from datetime_utils import DateTimeRange
from free_slots import find_free_slots
from models import EventSummary, TimeSlot


class FreeSlotService:
    """
    High-level service for finding free calendar slots.

    This class composes:

        EventSummary
            ↓
        BusyIntervalEngine
            ↓
        merged BusyInterval[]
            ↓
        find_free_slots()
            ↓
        TimeSlot[]

    It contains no:
        - Groq calls
        - Google API calls
        - natural-language interpretation
    """

    def __init__(
        self,
        busy_engine: BusyIntervalEngine | None = None,
    ) -> None:

        self.busy_engine = (
            busy_engine
            or BusyIntervalEngine()
        )

    def find_free_slots(
        self,
        *,
        events: list[EventSummary],
        window: DateTimeRange,
        minimum_duration_minutes: int = 1,
    ) -> list[TimeSlot]:
        """
        Find free slots inside the requested window.
        """

        busy_intervals = self.busy_engine.build(
            events
        )

        return find_free_slots(
            window=window,
            busy_intervals=busy_intervals,
            minimum_duration_minutes=minimum_duration_minutes,
        )