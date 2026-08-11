import os

import pytest

from models import CalendarOperation
from planner import SearchPlanner


pytestmark = pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY is not configured",
)


@pytest.fixture
def planner():
    return SearchPlanner()


def test_search_nexus_tomorrow(planner):
    result = planner.plan(
        "Show my Nexus AI events tomorrow"
    )

    assert result.operation == CalendarOperation.SEARCH
    assert result.query == "Nexus AI"
    assert result.date == "tomorrow"


def test_search_all_events_today(planner):
    result = planner.plan(
        "What events do I have today?"
    )

    assert result.operation == CalendarOperation.SEARCH
    assert result.query is None
    assert result.date == "today"


def test_search_dsa_this_week(planner):
    result = planner.plan(
        "Find my DSA events this week"
    )

    assert result.operation == CalendarOperation.SEARCH
    assert result.query == "DSA"
    assert result.date == "this week"


def test_search_with_time_range(planner):
    result = planner.plan(
        "Show my Nexus AI events tomorrow "
        "from 2 PM to 5 PM"
    )

    assert result.operation == CalendarOperation.SEARCH
    assert result.query == "Nexus AI"
    assert result.date == "tomorrow"
    assert result.start_time == "14:00"
    assert result.end_time == "17:00"


def test_search_without_date(planner):
    result = planner.plan(
        "Find my Nexus AI meetings"
    )

    assert result.operation == CalendarOperation.SEARCH
    assert result.query == "Nexus AI"
    assert result.date is None


def test_search_morning_without_inventing_times(planner):
    result = planner.plan(
        "Show my events tomorrow morning"
    )

    assert result.operation == CalendarOperation.SEARCH
    assert result.date == "tomorrow"

    # The model must not invent an exact time
    # merely because the user said "morning".
    assert result.start_time is None
    assert result.end_time is None


def test_search_no_calendar_api_parameters(planner):
    result = planner.plan(
        "Show my Nexus AI events tomorrow"
    )

    data = result.model_dump()

    assert "timeMin" not in data
    assert "timeMax" not in data
    assert "calendarId" not in data
    assert "singleEvents" not in data
    assert "orderBy" not in data


def test_search_12_pm(planner):
    result = planner.plan(
        "Show my events today from 12 PM to 2 PM"
    )

    assert result.start_time == "12:00"
    assert result.end_time == "14:00"


def test_search_12_am(planner):
    result = planner.plan(
        "Show my events today from 12 AM to 2 AM"
    )

    assert result.start_time == "00:00"
    assert result.end_time == "02:00"

def test_search_planner_schema_is_strict():
    schema = SearchPlanner._schema()

    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False

    assert set(schema["required"]) == {
        "operation",
        "query",
        "event_id",
        "date",
        "start_time",
        "end_time",
        "duration_minutes",
        "purpose",
        "timezone",
    }

    assert schema["properties"]["operation"]["enum"] == [
        "SEARCH"
    ]