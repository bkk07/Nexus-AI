from datetime import datetime

from busy_intervals import BusyInterval
from compiler import CalendarQueryCompiler
from connector.fake_calendar_client import FakeCalendarClient
from engine.busy import BusyIntervalEngine
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


def create_pipeline():
    """
    Build the complete deterministic Phase 6 pipeline.

    Fake Calendar
        ↓
    Search Engine
        ↓
    Busy Interval Engine
    """

    client = FakeCalendarClient(
        FAKE_EVENTS
    )

    search_engine = CalendarSearchEngine(
        client=client,
        compiler=CalendarQueryCompiler(
            default_timezone="Asia/Kolkata",
            default_search_days=30,
        ),
    )

    busy_engine = BusyIntervalEngine()

    return (
        client,
        search_engine,
        busy_engine,
    )


def test_no_events_produce_no_busy_intervals():

    client = FakeCalendarClient([])

    search_engine = CalendarSearchEngine(
        client=client,
    )

    busy_engine = BusyIntervalEngine()

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="Does Not Exist",
        date="tomorrow",
    )

    events = search_engine.search_events(
        request,
        reference=REFERENCE,
    )

    busy_intervals = busy_engine.build(
        events
    )

    assert events == []
    assert busy_intervals == []


def test_single_matching_event_becomes_busy_interval():

    client = FakeCalendarClient(
        [
            FAKE_EVENTS[0]
        ]
    )

    search_engine = CalendarSearchEngine(
        client=client,
    )

    busy_engine = BusyIntervalEngine()

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="Nexus AI Meeting",
        date="tomorrow",
    )

    events = search_engine.search_events(
        request,
        reference=REFERENCE,
    )

    busy_intervals = busy_engine.build(
        events
    )

    assert len(events) == 1
    assert len(busy_intervals) == 1

    assert (
        busy_intervals[0].start
        == FAKE_EVENTS[0].start
    )

    assert (
        busy_intervals[0].end
        == FAKE_EVENTS[0].end
    )

    assert (
        busy_intervals[0].source_event_ids
        == [FAKE_EVENTS[0].event_id]
    )


def test_multiple_events_are_converted_to_busy_intervals():

    client, search_engine, busy_engine = (
        create_pipeline()
    )

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
    )

    events = search_engine.search_events(
        request,
        reference=REFERENCE,
    )

    busy_intervals = busy_engine.build(
        events
    )

    assert len(events) == 3
    assert len(busy_intervals) == 3

    assert [
        interval.start
        for interval in busy_intervals
    ] == [
        FAKE_EVENTS[5].start,
        FAKE_EVENTS[0].start,
        FAKE_EVENTS[1].start,
    ]


def test_query_and_date_flow_through_pipeline():

    client, search_engine, busy_engine = (
        create_pipeline()
    )

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="DSA",
        date="tomorrow",
    )

    events = search_engine.search_events(
        request,
        reference=REFERENCE,
    )

    busy_intervals = busy_engine.build(
        events
    )

    assert len(events) == 1
    assert len(busy_intervals) == 1

    assert events[0].title == "DSA Study"

    assert busy_intervals[0].start == (
        FAKE_EVENTS[1].start
    )

    assert busy_intervals[0].end == (
        FAKE_EVENTS[1].end
    )


def test_time_range_flows_through_pipeline():

    client, search_engine, busy_engine = (
        create_pipeline()
    )

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
        start_time="18:00",
        end_time="22:00",
    )

    events = search_engine.search_events(
        request,
        reference=REFERENCE,
    )

    busy_intervals = busy_engine.build(
        events
    )

    assert len(events) == 1
    assert len(busy_intervals) == 1

    assert events[0].event_id == (
        "evt-dsa-1"
    )


def test_event_ids_are_preserved_through_pipeline():

    client, search_engine, busy_engine = (
        create_pipeline()
    )

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
    )

    events = search_engine.search_events(
        request,
        reference=REFERENCE,
    )

    busy_intervals = busy_engine.build(
        events
    )

    event_ids = {
        event.event_id
        for event in events
    }

    interval_event_ids = {
        event_id
        for interval in busy_intervals
        for event_id in interval.source_event_ids
    }

    assert interval_event_ids == event_ids


def test_calendar_search_query_is_actually_sent_to_client():

    client, search_engine, busy_engine = (
        create_pipeline()
    )

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="Nexus AI",
        date="tomorrow",
    )

    events = search_engine.search_events(
        request,
        reference=REFERENCE,
    )

    assert len(client.search_calls) == 1

    query = client.search_calls[0]

    assert query["q"] == "Nexus AI"

    assert query["singleEvents"] is True

    assert query["orderBy"] == "startTime"

    assert query["timeZone"] == "Asia/Kolkata"

    assert events