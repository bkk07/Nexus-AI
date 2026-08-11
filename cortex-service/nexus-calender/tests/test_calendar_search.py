from unittest.mock import Mock

from calendar_search import CalendarSearchExecutor


def build_service(response):

    service = Mock()

    events_resource = Mock()

    list_request = Mock()

    list_request.execute.return_value = response

    events_resource.list.return_value = list_request

    service.events.return_value = events_resource

    return service


def test_search_returns_events():

    service = build_service(
        {
            "items": [
                {
                    "id": "event-1",
                    "summary": "Nexus AI",
                    "start": {
                        "dateTime": (
                            "2026-08-12T14:00:00+05:30"
                        )
                    },
                    "end": {
                        "dateTime": (
                            "2026-08-12T15:00:00+05:30"
                        )
                    },
                    "status": "confirmed",
                    "htmlLink": (
                        "https://calendar.google.com/event/1"
                    ),
                }
            ]
        }
    )

    executor = CalendarSearchExecutor(
        service
    )

    result = executor.search(
        {
            "q": "Nexus AI",
            "timeMin": (
                "2026-08-12T00:00:00+05:30"
            ),
            "timeMax": (
                "2026-08-13T00:00:00+05:30"
            ),
            "singleEvents": True,
            "orderBy": "startTime",
            "timeZone": "Asia/Kolkata",
        }
    )

    assert len(result) == 1

    event = result[0]

    assert event.event_id == "event-1"
    assert event.summary == "Nexus AI"

    assert (
        event.start.isoformat()
        == "2026-08-12T14:00:00+05:30"
    )

    assert (
        event.end.isoformat()
        == "2026-08-12T15:00:00+05:30"
    )

    assert event.status == "confirmed"


def test_empty_calendar_returns_empty_list():

    service = build_service(
        {
            "items": []
        }
    )

    executor = CalendarSearchExecutor(
        service
    )

    result = executor.search(
        {
            "timeMin": (
                "2026-08-12T00:00:00+05:30"
            ),
            "timeMax": (
                "2026-08-13T00:00:00+05:30"
            ),
            "singleEvents": True,
            "orderBy": "startTime",
            "timeZone": "Asia/Kolkata",
        }
    )

    assert result == []


def test_all_day_event():

    service = build_service(
        {
            "items": [
                {
                    "id": "event-2",
                    "summary": "Holiday",
                    "start": {
                        "date": "2026-08-15"
                    },
                    "end": {
                        "date": "2026-08-16"
                    },
                }
            ]
        }
    )

    executor = CalendarSearchExecutor(
        service
    )

    result = executor.search(
        {
            "timeMin": (
                "2026-08-15T00:00:00+05:30"
            ),
            "timeMax": (
                "2026-08-16T00:00:00+05:30"
            ),
            "singleEvents": True,
            "orderBy": "startTime",
            "timeZone": "Asia/Kolkata",
        }
    )

    assert len(result) == 1

    event = result[0]

    assert event.event_id == "event-2"
    assert event.summary == "Holiday"

    assert event.start is None
    assert event.end is None

    assert event.start_is_all_day is True
    assert event.end_is_all_day is True


def test_google_parameters_are_forwarded():

    service = build_service(
        {
            "items": []
        }
    )

    executor = CalendarSearchExecutor(
        service
    )

    query = {
        "q": "Nexus AI",
        "timeMin": (
            "2026-08-12T00:00:00+05:30"
        ),
        "timeMax": (
            "2026-08-13T00:00:00+05:30"
        ),
        "singleEvents": True,
        "orderBy": "startTime",
        "timeZone": "Asia/Kolkata",
    }

    executor.search(query)

    service.events.return_value.list.assert_called_once_with(
        calendarId="primary",
        **query,
    )