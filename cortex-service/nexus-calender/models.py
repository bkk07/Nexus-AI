from __future__ import annotations
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class CalendarOperation(str, Enum):
    SEARCH = "SEARCH"
    COUNT = "COUNT"
    FETCH = "FETCH"
    CHECK_AVAILABILITY = "CHECK_AVAILABILITY"
    FIND_FREE_SLOTS = "FIND_FREE_SLOTS"
    FIND_NEXT_FREE_SLOT = "FIND_NEXT_FREE_SLOT"
    FIND_BEST_SLOT = "FIND_BEST_SLOT"


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