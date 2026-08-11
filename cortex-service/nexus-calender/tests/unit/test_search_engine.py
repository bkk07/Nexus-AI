from datetime import datetime

import pytest

from compiler import CalendarQueryCompiler
from connector.errors import CalendarConnectorError
from connector.fake_calendar_client import FakeCalendarClient
from engine.search import CalendarSearchEngine
from fixtures.fake_calendar_data import FAKE_EVENTS
from models import CalendarOperation, CalendarRequest


REFERENCE = datetime(
    2026,
    8,
    11,
    10,
    0,
)


@pytest.fixture
def client():

    return FakeCalendarClient(
        FAKE_EVENTS
    )


@pytest.fixture
def engine(client):

    return CalendarSearchEngine(
        client=client,
        compiler=CalendarQueryCompiler(
            default_timezone="Asia/Kolkata",
            default_search_days=30,
        ),
    )


def test_no_results(engine):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="Does Not Exist",
        date="tomorrow",
    )

    result = engine.search_events(
        request,
        reference=REFERENCE,
    )

    assert result == []


def test_one_result(engine):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="Nexus AI Meeting",
        date="tomorrow",
    )

    result = engine.search_events(
        request,
        reference=REFERENCE,
    )

    assert len(result) == 1

    assert result[0].event_id == (
        "evt-nexus-1"
    )


def test_multiple_results(engine):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
    )

    result = engine.search_events(
        request,
        reference=REFERENCE,
    )

    assert len(result) == 3

    assert [
        event.event_id
        for event in result
    ] == [
        "evt-recurring-2",
        "evt-nexus-1",
        "evt-dsa-1",
    ]


def test_query_only(engine):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="Nexus",
    )

    result = engine.search_events(
        request,
        reference=REFERENCE,
    )

    assert len(result) == 2

    assert {
        event.event_id
        for event in result
    } == {
        "evt-nexus-1",
        "evt-project-1",
    }


def test_date_only(engine):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="today",
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


def test_query_and_date(engine):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="DSA",
        date="tomorrow",
    )

    result = engine.search_events(
        request,
        reference=REFERENCE,
    )

    assert len(result) == 1

    assert result[0].event_id == (
        "evt-dsa-1"
    )


def test_time_of_day_filter(engine):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
        start_time="18:00",
        end_time="22:00",
    )

    result = engine.search_events(
        request,
        reference=REFERENCE,
    )

    assert len(result) == 1

    assert result[0].event_id == (
        "evt-dsa-1"
    )


def test_results_are_event_summary_objects(
    engine,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
    )

    result = engine.search_events(
        request,
        reference=REFERENCE,
    )

    assert result

    for event in result:

        assert event.__class__.__name__ == (
            "EventSummary"
        )

        assert isinstance(
            event.event_id,
            str,
        )

        assert isinstance(
            event.title,
            str,
        )

        assert event.start is not None
        assert event.end is not None


def test_only_fixture_events_are_returned(
    engine,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
    )

    result = engine.search_events(
        request,
        reference=REFERENCE,
    )

    fixture_ids = {
        event.event_id
        for event in FAKE_EVENTS
    }

    result_ids = {
        event.event_id
        for event in result
    }

    assert result_ids <= fixture_ids


def test_connector_error_is_typed():

    class BrokenClient:

        def search(self, query):

            raise CalendarConnectorError(
                "test failure"
            )

    engine = CalendarSearchEngine(
        client=BrokenClient()
    )

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="today",
    )

    with pytest.raises(
        CalendarConnectorError
    ):

        engine.search_events(
            request,
            reference=REFERENCE,
        )


def test_non_search_operation_is_rejected(
    engine,
):

    request = CalendarRequest(
        operation=CalendarOperation.COUNT,
        date="today",
    )

    with pytest.raises(ValueError):

        engine.search_events(
            request,
            reference=REFERENCE,
        )