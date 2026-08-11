from __future__ import annotations

from datetime import datetime, time, timedelta

from datetime_utils import DateTimeRange
from free_slot_service import FreeSlotService
from models import EventSummary, TimeSlot


class NextSlotService:

    def __init__(
        self,
        free_slot_service: FreeSlotService | None = None,
    ) -> None:
        self.free_slot_service = (
            free_slot_service
            or FreeSlotService()
        )

    def find_next_free_slot(
        self,
        events: list[EventSummary],
        earliest_start: datetime,
        duration_minutes: int,
        horizon_days: int = 14,
    ) -> TimeSlot | None:

        if duration_minutes <= 0:
            raise ValueError(
                "duration_minutes must be greater than zero"
            )

        if horizon_days <= 0:
            raise ValueError(
                "horizon_days must be greater than zero"
            )

        if earliest_start.tzinfo is None:
            raise ValueError(
                "earliest_start must be timezone-aware"
            )

        current_day = earliest_start.date()

        for day_offset in range(horizon_days):

            day = current_day + timedelta(
                days=day_offset
            )

            day_start = datetime.combine(
                day,
                time.min,
                tzinfo=earliest_start.tzinfo,
            )

            day_end = datetime.combine(
                day,
                time.max,
                tzinfo=earliest_start.tzinfo,
            )

            # First day starts from "now".
            if day_offset == 0:
                window_start = earliest_start
            else:
                window_start = day_start

            window = DateTimeRange(
                start=window_start,
                end=day_end,
            )

            day_events = [
                event
                for event in events
                if event.start < window.end
                and event.end > window.start
            ]

            slots = self.free_slot_service.find_free_slots(
                events=day_events,
                window=window,
                minimum_duration_minutes=duration_minutes,
            )

            if slots:
                return slots[0]

        return None