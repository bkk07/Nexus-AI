import pytest
from pydantic import ValidationError

from models import (
    CalendarOperation,
    CalendarRequest,
)


def test_search_request():
    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="Nexus AI",
        date="tomorrow",
    )

    assert request.operation == CalendarOperation.SEARCH
    assert request.query == "Nexus AI"
    assert request.date == "tomorrow"


def test_count_request():
    request = CalendarRequest(
        operation=CalendarOperation.COUNT,
        date="today",
    )

    assert request.operation == CalendarOperation.COUNT
    assert request.date == "today"


def test_fetch_request():
    request = CalendarRequest(
        operation=CalendarOperation.FETCH,
        event_id="event-123",
    )

    assert request.operation == CalendarOperation.FETCH
    assert request.event_id == "event-123"


def test_check_availability_request():
    request = CalendarRequest(
        operation=CalendarOperation.CHECK_AVAILABILITY,
        date="tomorrow",
        start_time="19:00",
        end_time="21:00",
    )

    assert (
        request.operation
        == CalendarOperation.CHECK_AVAILABILITY
    )

    assert request.start_time == "19:00"
    assert request.end_time == "21:00"


def test_find_free_slots_request():
    request = CalendarRequest(
        operation=CalendarOperation.FIND_FREE_SLOTS,
        date="tomorrow",
        duration_minutes=120,
    )

    assert (
        request.operation
        == CalendarOperation.FIND_FREE_SLOTS
    )

    assert request.duration_minutes == 120


def test_find_next_free_slot_request():
    request = CalendarRequest(
        operation=CalendarOperation.FIND_NEXT_FREE_SLOT,
        duration_minutes=90,
    )

    assert (
        request.operation
        == CalendarOperation.FIND_NEXT_FREE_SLOT
    )

    assert request.duration_minutes == 90


def test_find_best_slot_request():
    request = CalendarRequest(
        operation=CalendarOperation.FIND_BEST_SLOT,
        date="tomorrow",
        duration_minutes=120,
        purpose="DSA",
    )

    assert (
        request.operation
        == CalendarOperation.FIND_BEST_SLOT
    )

    assert request.duration_minutes == 120
    assert request.purpose == "DSA"


def test_default_timezone():
    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
    )

    assert request.timezone == "Asia/Kolkata"


def test_custom_timezone():
    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        timezone="America/New_York",
    )

    assert request.timezone == "America/New_York"


def test_duration_must_be_positive():
    with pytest.raises(ValidationError):
        CalendarRequest(
            operation=CalendarOperation.FIND_FREE_SLOTS,
            duration_minutes=0,
        )


def test_negative_duration_is_invalid():
    with pytest.raises(ValidationError):
        CalendarRequest(
            operation=CalendarOperation.FIND_FREE_SLOTS,
            duration_minutes=-30,
        )


def test_empty_query_becomes_none():
    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="   ",
    )

    assert request.query is None


def test_empty_event_id_becomes_none():
    request = CalendarRequest(
        operation=CalendarOperation.FETCH,
        event_id="   ",
    )

    assert request.event_id is None


def test_groq_safe_schema():
    schema = CalendarRequest.model_json_schema()

    assert "properties" in schema

    properties = schema["properties"]

    assert "operation" in properties
    assert "query" in properties
    assert "event_id" in properties
    assert "date" in properties
    assert "start_time" in properties
    assert "end_time" in properties
    assert "duration_minutes" in properties
    assert "purpose" in properties
    assert "timezone" in properties

    # We do not want unrestricted dict[str, Any]
    # in the LLM-facing schema.
    for property_schema in properties.values():
        assert property_schema.get("additionalProperties") is not True