import os
from datetime import datetime

import pytest

from compiler import CalendarQueryCompiler
from connector.fake_calendar_client import FakeCalendarClient
from engine.search import CalendarSearchEngine
from fixtures.fake_calendar_data import FAKE_EVENTS
from planner import SearchPlanner


REFERENCE = datetime(
    2026,
    8,
    11,
    10,
    0,
)


@pytest.fixture
def planner():

    if not os.getenv("GROQ_API_KEY"):
        pytest.skip(
            "GROQ_API_KEY not configured."
        )

    return SearchPlanner()


@pytest.fixture
def engine():

    client = FakeCalendarClient(
        FAKE_EVENTS
    )

    return CalendarSearchEngine(
        client=client,
        compiler=CalendarQueryCompiler(
            default_timezone="Asia/Kolkata",
            default_search_days=30,
        ),
    )


def test_natural_language_search(
    planner,
    engine,
):

    request = planner.plan(
        "Show my Nexus AI events tomorrow"
    )

    result = engine.search_events(
        request,
        reference=REFERENCE,
    )

    assert [
        event.event_id
        for event in result
    ] == [
        "evt-nexus-1"
    ]


def test_natural_language_today(
    planner,
    engine,
):

    request = planner.plan(
        "What events do I have today?"
    )

    result = engine.search_events(
        request,
        reference=REFERENCE,
    )

    assert {
        event.event_id
        for event in result
    } == {
        "evt-meeting-1",
        "evt-recurring-1",
    }


def test_natural_language_dsa(
    planner,
    engine,
):

    request = planner.plan(
        "Find my DSA events tomorrow"
    )

    result = engine.search_events(
        request,
        reference=REFERENCE,
    )

    assert [
        event.event_id
        for event in result
    ] == [
        "evt-dsa-1"
    ]