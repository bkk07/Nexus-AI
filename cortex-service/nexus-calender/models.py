from __future__ import annotations
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Literal

class CalendarOperation(str, Enum):
    SEARCH = "SEARCH"
    COUNT = "COUNT"
    FETCH = "FETCH"
    CHECK_AVAILABILITY = "CHECK_AVAILABILITY"
    FIND_FREE_SLOTS = "FIND_FREE_SLOTS"
    FIND_NEXT_FREE_SLOT = "FIND_NEXT_FREE_SLOT"
    FIND_BEST_SLOT = "FIND_BEST_SLOT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class CalendarRequest(BaseModel):
    """
    Semantic representation of a user's Calendar request.

    This model represents user intent.
    It does NOT represent Google Calendar API parameters.
    """

    operation: CalendarOperation

    # Search/filter information
    query: str | None = None

    # Explicit event identification
    event_id: str | None = None

    # Natural date representation.
    #
    # Examples:
    #   today
    #   tomorrow
    #   Friday
    #   2026-08-15
    date: str | None = None

    # User-requested time range.
    #
    # Examples:
    #   07:00
    #   19:00
    start_time: str | None = None
    end_time: str | None = None

    # Required duration for availability/scheduling.
    duration_minutes: int | None = Field(
        default=None,
        gt=0,
    )

    # Why the user wants the slot.
    #
    # Example:
    #   DSA
    #   project work
    #   coding
    purpose: str | None = None

    # User/project timezone.
    timezone: str = "Asia/Kolkata"

    @field_validator("query", "event_id", "date", "purpose")
    @classmethod
    def normalize_optional_strings(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None


class CalendarEvent(BaseModel):
    """
    Normalized representation of a Google Calendar event.

    This is our application's representation.
    It is NOT the raw Google Calendar API response.
    """

    event_id: str
    summary: str | None = None

    start: datetime | None = None
    end: datetime | None = None

    start_is_all_day: bool = False
    end_is_all_day: bool = False

    status: str | None = None
    html_link: str | None = None


class EventSummary(BaseModel):
    """
    Stable application-level representation of a calendar event.

    The rest of the Calendar system should depend on this model,
    not on raw Google Calendar API dictionaries.
    """

    event_id: str
    title: str
    start: datetime
    end: datetime

    location: str | None = None
    description: str | None = None

class TimeSlot(BaseModel):
    start: datetime
    end: datetime
    duration_minutes: int

class TimeSlot(BaseModel):
    """
    Represents a contiguous free period in the calendar.

    This is an application-level representation.
    It does not contain Google Calendar API data.
    """

    start: datetime
    end: datetime
    duration_minutes: int = Field(
        gt=0,
    )


class RankedSlot(BaseModel):
    """
    A free slot together with its deterministic ranking score.

    The score is calculated entirely by Python.
    No LLM is involved in ranking.
    """

    slot: TimeSlot
    score: float
    reasons: list[str] = Field(default_factory=list)


class CalendarCreateRequest(BaseModel):
    """
    Normalized representation of a calendar event creation request.

    This model represents application-level intent.
    It does not contain Google Calendar API parameters.
    """

    title: str

    start: datetime

    end: datetime

    location: str | None = None

    description: str | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(
        cls,
        value: str,
    ) -> str:

        value = value.strip()

        if not value:
            raise ValueError(
                "Event title cannot be empty."
            )

        return value

    @field_validator("end")
    @classmethod
    def validate_end(
        cls,
        value: datetime,
        info,
    ) -> datetime:

        start = info.data.get("start")

        if start is not None and value <= start:
            raise ValueError(
                "Event end must be after event start."
            )

        return value

    @field_validator("location", "description")
    @classmethod
    def normalize_optional_strings(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        return value or None

class CreateOutcome(BaseModel):
    """
    Result of a safe calendar creation attempt.

    The status explains exactly why creation did or did not occur.
    """

    status: Literal[
        "created",
        "duplicate_blocked",
        "conflict_blocked",
        "invalid",
    ]

    event: EventSummary | None = None

    existing_duplicate: EventSummary | None = None

    conflicts: list[EventSummary] = Field(
        default_factory=list,
    )

    message: str

class FetchOutcome(BaseModel):
    """
    Result of safely resolving a single calendar event.
    """

    status: Literal[
        "found",
        "not_found",
        "ambiguous",
    ]

    event: EventSummary | None = None

    candidates: list[EventSummary] = Field(
        default_factory=list,
    )
class CalendarFetchRequest(BaseModel):
    """
    Semantic representation of a request to fetch
    exactly one calendar event.
    """

    operation: Literal[
        CalendarOperation.FETCH
    ]

    event_id: str | None = None

    query: str | None = None

    date: str | None = None

    @field_validator(
        "event_id",
        "query",
        "date",
    )
    @classmethod
    def normalize_optional_strings(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        return value or None

class CalendarUpdateRequest(BaseModel):
    """
    Normalized representation of a calendar event update request.

    Exactly one event must be resolved before any update occurs.

    The event can be identified using:
        - event_id
        - query

    Only supplied fields are changed.
    """

    operation: CalendarOperation

    event_id: str | None = None
    query: str | None = None

    new_title: str | None = None
    new_start: datetime | None = None
    new_end: datetime | None = None
    new_description: str | None = None
    new_location: str | None = None

    @field_validator(
        "event_id",
        "query",
        "new_title",
        "new_description",
        "new_location",
    )
    @classmethod
    def normalize_optional_strings(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        return value or None

    @field_validator("new_end")
    @classmethod
    def validate_new_end(
        cls,
        value: datetime | None,
        info,
    ) -> datetime | None:

        if value is None:
            return None

        new_start = info.data.get("new_start")

        if (
            new_start is not None
            and value <= new_start
        ):
            raise ValueError(
                "new_end must be after new_start."
            )

        return value

class UpdateOutcome(BaseModel):
    """
    Result of a safe calendar update attempt.
    """

    status: Literal[
        "updated",
        "not_found",
        "ambiguous",
        "conflict_blocked",
        "invalid",
    ]

    event: EventSummary | None = None

    candidates: list[EventSummary] = Field(
        default_factory=list,
    )

    conflicts: list[EventSummary] = Field(
        default_factory=list,
    )

    message: str = ""


class CalendarDeleteRequest(BaseModel):
    """
    Normalized representation of a calendar event
    deletion request.

    The request identifies the event either by:
    - explicit event_id
    - natural-language query
    """

    operation: CalendarOperation

    event_id: str | None = None

    query: str | None = None

    @field_validator("event_id", "query")
    @classmethod
    def normalize_optional_strings(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        return value or None


class DeleteOutcome(BaseModel):
    """
    Result of a safe calendar deletion attempt.
    """

    status: Literal[
        "deleted",
        "not_found",
        "ambiguous",
        "invalid",
    ]

    event: EventSummary | None = None

    candidates: list[EventSummary] = Field(
        default_factory=list,
    )

    message: str


class AvailabilityOutcome(BaseModel):
    """
    Result of checking whether a requested time range
    is available.
    """

    status: Literal[
        "available",
        "conflict",
        "invalid",
    ]

    conflicts: list[EventSummary] = Field(
        default_factory=list,
    )

    message: str



class CalendarMultiConstraintRequest(BaseModel):
    """
    Semantic representation of a compound scheduling request.

    This model separates hard constraints from soft preferences.

    Hard constraints:
        - hard_start_time
        - hard_end_time
        - deadline

    Soft preferences:
        - preferred_start_time
        - preferred_end_time

    Splitting:
        - split_required
        - number_of_blocks

    The model represents user intent only.
    It does not perform scheduling itself.
    """

    duration_minutes: int = Field(
        gt=0,
    )

    # -------------------------------------------------
    # Hard window constraints
    # -------------------------------------------------

    hard_start_time: str | None = None

    hard_end_time: str | None = None

    # -------------------------------------------------
    # Soft preference window
    # -------------------------------------------------

    preferred_start_time: str | None = None

    preferred_end_time: str | None = None

    # -------------------------------------------------
    # Deadline
    # -------------------------------------------------

    deadline: datetime | None = None

    # -------------------------------------------------
    # Multi-block scheduling
    # -------------------------------------------------

    split_required: bool = False

    number_of_blocks: int | None = Field(
        default=None,
        gt=0,
    )

    # -------------------------------------------------
    # Optional purpose
    # -------------------------------------------------

    purpose: str | None = None

    # -------------------------------------------------
    # Timezone
    # -------------------------------------------------

    timezone: str = "Asia/Kolkata"

    @field_validator(
        "hard_start_time",
        "hard_end_time",
        "preferred_start_time",
        "preferred_end_time",
        "purpose",
    )
    @classmethod
    def normalize_optional_strings(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        return value or None

    @field_validator("number_of_blocks")
    @classmethod
    def validate_number_of_blocks(
        cls,
        value: int | None,
    ) -> int | None:

        if value is not None and value < 1:
            raise ValueError(
                "number_of_blocks must be positive."
            )

        return value