from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from best_slot import BestSlotService
from busy_intervals import (
    events_to_busy_intervals,
    merge_busy_intervals,
)
from datetime_utils import DateTimeRange
from engine.fetch import CalendarFetchService
from free_slots import find_free_slots
from models import (
    CalendarFetchRequest,
    EventSummary,
    RankedSlot,
)


class RescheduleProposal(BaseModel):
    """
    Possible alternatives for an existing calendar event.

    This is a proposal only.

    IMPORTANT:
    Creating a RescheduleProposal never modifies
    Google Calendar.
    """

    original_event: EventSummary

    options: list[RankedSlot] = Field(
        default_factory=list,
    )


class RescheduleOutcome(BaseModel):
    """
    Result of resolving a reschedule request.

    Resolution can fail because the target was:

        - not found
        - ambiguous

    When the target is ambiguous, candidates are
    returned so the caller can ask the user to choose.

    No calendar event is modified by this model.
    """

    status: Literal[
        "found",
        "not_found",
        "ambiguous",
    ]

    proposal: RescheduleProposal | None = None

    candidates: list[EventSummary] = Field(
        default_factory=list,
    )

    message: str = ""


class RescheduleService:
    """
    Generate ranked alternatives for an existing event.

    Architecture:

        Phase 13 Fetch
              ↓
        resolve target
              ↓
        exclude target event
              ↓
        convert remaining events
        into busy intervals
              ↓
        find free slots
              ↓
        Phase 10 ranking
              ↓
        RescheduleProposal

    This service NEVER calls update_event().
    """

    def __init__(
        self,
        client,
        best_slot_service: BestSlotService | None = None,
    ) -> None:

        self.client = client

        self.fetch_service = (
            CalendarFetchService(
                client
            )
        )

        self.best_slot_service = (
            best_slot_service
            if best_slot_service is not None
            else BestSlotService()
        )

    def find_reschedule_options(
        self,
        request: CalendarFetchRequest,
        *,
        search_start: datetime,
        search_end: datetime,
        duration_minutes: int | None = None,
        preferred_start=None,
        preferred_window_start=None,
        preferred_window_end=None,
        minimum_duration_minutes: int = 1,
    ) -> RescheduleOutcome:
        """
        Find and rank alternative slots.

        This method ONLY proposes alternatives.

        It does NOT:
            - update an event
            - delete an event
            - create an event

        The caller must explicitly select one option and
        then use the Phase 14 update flow separately.
        """

        if search_end <= search_start:
            raise ValueError(
                "search_end must be after search_start."
            )

        if minimum_duration_minutes <= 0:
            raise ValueError(
                "minimum_duration_minutes must "
                "be positive."
            )

        # --------------------------------------------------
        # 1. Resolve target using Phase 13
        # --------------------------------------------------

        fetch_result = (
            self.fetch_service.fetch(
                request
            )
        )

        # --------------------------------------------------
        # Target not found
        # --------------------------------------------------

        if fetch_result.status == "not_found":

            return RescheduleOutcome(
                status="not_found",
                message=(
                    "The event to reschedule "
                    "could not be found."
                ),
            )

        # --------------------------------------------------
        # Target ambiguous
        # --------------------------------------------------

        if fetch_result.status == "ambiguous":

            return RescheduleOutcome(
                status="ambiguous",
                candidates=(
                    fetch_result.candidates
                ),
                message=(
                    "Multiple events matched. "
                    "Please select the event "
                    "to reschedule."
                ),
            )

        # --------------------------------------------------
        # Target found
        # --------------------------------------------------

        original_event = (
            fetch_result.event
        )

        if original_event is None:
            return RescheduleOutcome(
                status="not_found",
                message=(
                    "The event to reschedule "
                    "could not be resolved."
                ),
            )

        # --------------------------------------------------
        # 2. Determine requested duration
        # --------------------------------------------------

        if duration_minutes is None:

            duration_minutes = int(
                (
                    original_event.end
                    - original_event.start
                ).total_seconds()
                // 60
            )

        if duration_minutes <= 0:
            raise ValueError(
                "duration_minutes must be positive."
            )

        # --------------------------------------------------
        # 3. Search events in the requested horizon
        # --------------------------------------------------

        events = self.client.search(
            {
                "timeMin": (
                    search_start.isoformat()
                ),
                "timeMax": (
                    search_end.isoformat()
                ),
                "singleEvents": True,
                "orderBy": "startTime",
            }
        )

        # --------------------------------------------------
        # 4. CRITICAL SELF-EXCLUSION
        #
        # The event being rescheduled must NOT remain
        # a conflict with its own replacement.
        # --------------------------------------------------

        other_events = [
            event
            for event in events
            if event.event_id
            != original_event.event_id
        ]

        # --------------------------------------------------
        # 5. Convert remaining calendar events to busy
        # --------------------------------------------------

        busy_intervals = (
            events_to_busy_intervals(
                other_events
            )
        )

        busy_intervals = (
            merge_busy_intervals(
                busy_intervals
            )
        )

        # --------------------------------------------------
        # 6. Build search window
        # --------------------------------------------------

        window = DateTimeRange(
            start=search_start,
            end=search_end,
        )

        # --------------------------------------------------
        # 7. Find genuinely free slots
        # --------------------------------------------------

        free_slots = find_free_slots(
            window=window,
            busy_intervals=busy_intervals,
            minimum_duration_minutes=(
                max(
                    minimum_duration_minutes,
                    duration_minutes,
                )
            ),
        )

        # --------------------------------------------------
        # 8. No viable alternative
        # --------------------------------------------------

        if not free_slots:

            return RescheduleOutcome(
                status="found",
                proposal=RescheduleProposal(
                    original_event=(
                        original_event
                    ),
                    options=[],
                ),
                message=(
                    "No viable alternative "
                    "was found within the "
                    "search horizon."
                ),
            )

        # --------------------------------------------------
        # 9. Rank using Phase 10
        # --------------------------------------------------

        ranked = (
            self.best_slot_service.rank_slots(
                slots=free_slots,
                requested_duration_minutes=(
                    duration_minutes
                ),
                preferred_start=(
                    preferred_start
                ),
                preferred_window_start=(
                    preferred_window_start
                ),
                preferred_window_end=(
                    preferred_window_end
                ),
            )
        )

        # --------------------------------------------------
        # 10. Return proposal only.
        #
        # NEVER call:
        #
        # self.client.update_event(...)
        #
        # here.
        # --------------------------------------------------

        proposal = RescheduleProposal(
            original_event=original_event,
            options=ranked,
        )

        return RescheduleOutcome(
            status="found",
            proposal=proposal,
            message=(
                "Reschedule alternatives "
                "generated successfully."
            ),
        )