from datetime import datetime

from availability_service import AvailabilityService
from busy_intervals import BusyInterval
from compiler import CalendarQueryCompiler
from connector.fake_calendar_client import FakeCalendarClient
from engine.busy import BusyIntervalEngine
from engine.search import CalendarSearchEngine
from models import CalendarOperation, CalendarRequest
from fixtures.fake_calendar_data import FAKE_EVENTS


REFERENCE = datetime(
    2026,
    8,
    11,
    10,
    0,
)


def build_pipeline():
    """
    Complete deterministic availability pipeline:

        FakeCalendarClient
                ↓
        CalendarSearchEngine
                ↓
        EventSummary[]
                ↓
        BusyIntervalEngine
                ↓
        BusyInterval[]
                ↓
        AvailabilityService
                ↓
        AvailabilityResult
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

    availability_service = AvailabilityService(
        default_timezone="Asia/Kolkata"
    )

    return (
        client,
        search_engine,
        busy_engine,
        availability_service,
    )


def test_free_time_through_complete_pipeline():

    (
        client,
        search_engine,
        busy_engine,
        availability_service,
    ) = build_pipeline()

    request = CalendarRequest(
        operation=CalendarOperation.CHECK_AVAILABILITY,
        date="tomorrow",
        start_time="12:00",
        end_time="13:00",
    )

    # Search tomorrow's calendar.
    search_request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
    )

    events = search_engine.search_events(
        search_request,
        reference=REFERENCE,
    )

    # Convert events into merged busy intervals.
    busy_intervals = busy_engine.build(
        events
    )

    # Check requested availability.
    result = availability_service.check(
        request,
        busy_intervals,
        reference=REFERENCE,
    )

    assert result.available is True
    assert result.conflicts == []


def test_busy_time_through_complete_pipeline():

    (
        client,
        search_engine,
        busy_engine,
        availability_service,
    ) = build_pipeline()

    request = CalendarRequest(
        operation=CalendarOperation.CHECK_AVAILABILITY,
        date="tomorrow",
        start_time="19:00",
        end_time="21:00",
    )

    search_request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
    )

    events = search_engine.search_events(
        search_request,
        reference=REFERENCE,
    )

    busy_intervals = busy_engine.build(
        events
    )

    result = availability_service.check(
        request,
        busy_intervals,
        reference=REFERENCE,
    )

    assert result.available is False

    assert len(result.conflicts) > 0


def test_conflicting_event_ids_are_preserved():

    (
        client,
        search_engine,
        busy_engine,
        availability_service,
    ) = build_pipeline()

    request = CalendarRequest(
        operation=CalendarOperation.CHECK_AVAILABILITY,
        date="tomorrow",
        start_time="19:00",
        end_time="21:00",
    )

    search_request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
    )

    events = search_engine.search_events(
        search_request,
        reference=REFERENCE,
    )

    busy_intervals = busy_engine.build(
        events
    )

    result = availability_service.check(
        request,
        busy_intervals,
        reference=REFERENCE,
    )

    conflict_event_ids = {
        event_id
        for interval in result.conflicts
        for event_id in interval.source_event_ids
    }

    assert conflict_event_ids


def test_boundary_touching_is_free_through_pipeline():

    (
        client,
        search_engine,
        busy_engine,
        availability_service,
    ) = build_pipeline()

    # Our fake calendar contains an event ending at 18:00.
    request = CalendarRequest(
        operation=CalendarOperation.CHECK_AVAILABILITY,
        date="tomorrow",
        start_time="18:00",
        end_time="19:00",
    )

    search_request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
    )

    events = search_engine.search_events(
        search_request,
        reference=REFERENCE,
    )

    busy_intervals = busy_engine.build(
        events
    )

    result = availability_service.check(
        request,
        busy_intervals,
        reference=REFERENCE,
    )

    assert result.available is True
    assert result.conflicts == []


def test_query_does_not_affect_availability_engine():

    (
        client,
        search_engine,
        busy_engine,
        availability_service,
    ) = build_pipeline()

    search_request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
    )

    events = search_engine.search_events(
        search_request,
        reference=REFERENCE,
    )

    busy_intervals = busy_engine.build(
        events
    )

    request = CalendarRequest(
        operation=CalendarOperation.CHECK_AVAILABILITY,
        query="DSA",
        date="tomorrow",
        start_time="19:00",
        end_time="21:00",
    )

    result = availability_service.check(
        request,
        busy_intervals,
        reference=REFERENCE,
    )

    assert result.available is False