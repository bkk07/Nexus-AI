from datetime import datetime

import pytest

from compiler import CalendarQueryCompiler
from models import (
    CalendarOperation,
    CalendarRequest,
)


REFERENCE = datetime(
    2026,
    8,
    11,
    10,
    0,
)


@pytest.fixture
def compiler():
    return CalendarQueryCompiler(
        default_timezone="Asia/Kolkata",
        default_search_days=30,
    )


# =========================================================
# BASIC SEARCH
# =========================================================


def test_search_today(
    compiler,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="today",
    )

    result = compiler.compile_search(
        request,
        reference=REFERENCE,
    )

    assert result == {
        "timeMin": "2026-08-11T00:00:00+05:30",
        "timeMax": "2026-08-12T00:00:00+05:30",
        "singleEvents": True,
        "orderBy": "startTime",
        "timeZone": "Asia/Kolkata",
    }


def test_search_with_query(
    compiler,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="Nexus AI",
        date="tomorrow",
    )

    result = compiler.compile_search(
        request,
        reference=REFERENCE,
    )

    assert result == {
        "q": "Nexus AI",
        "timeMin": "2026-08-12T00:00:00+05:30",
        "timeMax": "2026-08-13T00:00:00+05:30",
        "singleEvents": True,
        "orderBy": "startTime",
        "timeZone": "Asia/Kolkata",
    }


# =========================================================
# TIME RANGE
# =========================================================


def test_search_with_time_range(
    compiler,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="Nexus AI",
        date="tomorrow",
        start_time="14:00",
        end_time="17:00",
    )

    result = compiler.compile_search(
        request,
        reference=REFERENCE,
    )

    assert result == {
        "q": "Nexus AI",
        "timeMin": "2026-08-12T14:00:00+05:30",
        "timeMax": "2026-08-12T17:00:00+05:30",
        "singleEvents": True,
        "orderBy": "startTime",
        "timeZone": "Asia/Kolkata",
    }


def test_search_with_12_hour_time(
    compiler,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
        start_time="2 PM",
        end_time="5 PM",
    )

    result = compiler.compile_search(
        request,
        reference=REFERENCE,
    )

    assert result["timeMin"] == (
        "2026-08-12T14:00:00+05:30"
    )

    assert result["timeMax"] == (
        "2026-08-12T17:00:00+05:30"
    )


# =========================================================
# OVERNIGHT
# =========================================================


def test_overnight_time_range(
    compiler,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="Lunch",
        date="today",
        start_time="12 PM",
        end_time="1 AM",
    )

    result = compiler.compile_search(
        request,
        reference=REFERENCE,
    )

    assert result["timeMin"] == (
        "2026-08-11T12:00:00+05:30"
    )

    assert result["timeMax"] == (
        "2026-08-12T01:00:00+05:30"
    )


# =========================================================
# RELATIVE DATES
# =========================================================


def test_last_7_days(
    compiler,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="Nexus AI",
        date="last 7 days",
    )

    result = compiler.compile_search(
        request,
        reference=REFERENCE,
    )

    assert result["q"] == "Nexus AI"

    assert result["timeMin"] == (
        "2026-08-05T00:00:00+05:30"
    )

    assert result["timeMax"] == (
        "2026-08-12T00:00:00+05:30"
    )


def test_next_7_days(
    compiler,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="next 7 days",
    )

    result = compiler.compile_search(
        request,
        reference=REFERENCE,
    )

    assert result["timeMin"] == (
        "2026-08-11T00:00:00+05:30"
    )

    assert result["timeMax"] == (
        "2026-08-18T00:00:00+05:30"
    )


def test_this_week(
    compiler,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="this week",
    )

    result = compiler.compile_search(
        request,
        reference=REFERENCE,
    )

    assert result["timeMin"] == (
        "2026-08-10T00:00:00+05:30"
    )

    assert result["timeMax"] == (
        "2026-08-17T00:00:00+05:30"
    )


# =========================================================
# QUERY ONLY
# =========================================================


def test_query_without_date_is_bounded(
    compiler,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="Nexus AI",
    )

    result = compiler.compile_search(
        request,
        reference=REFERENCE,
    )

    assert result["q"] == "Nexus AI"

    assert result["timeMin"] == (
        "2026-08-11T10:00:00+05:30"
    )

    assert result["timeMax"] == (
        "2026-09-10T10:00:00+05:30"
    )


def test_empty_query_is_not_sent(
    compiler,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        query="   ",
        date="today",
    )

    result = compiler.compile_search(
        request,
        reference=REFERENCE,
    )

    assert "q" not in result


# =========================================================
# TIME VALIDATION
# =========================================================


def test_only_start_time_is_invalid(
    compiler,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="today",
        start_time="10:00",
    )

    with pytest.raises(ValueError):
        compiler.compile_search(
            request,
            reference=REFERENCE,
        )


def test_only_end_time_is_invalid(
    compiler,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="today",
        end_time="12:00",
    )

    with pytest.raises(ValueError):
        compiler.compile_search(
            request,
            reference=REFERENCE,
        )


def test_invalid_time_format(
    compiler,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="today",
        start_time="hello",
        end_time="12:00",
    )

    with pytest.raises(ValueError):
        compiler.compile_search(
            request,
            reference=REFERENCE,
        )


# =========================================================
# OPERATION VALIDATION
# =========================================================


def test_only_search_is_supported(
    compiler,
):

    request = CalendarRequest(
        operation=CalendarOperation.COUNT,
        date="today",
    )

    with pytest.raises(ValueError):
        compiler.compile_search(
            request,
            reference=REFERENCE,
        )


# =========================================================
# TIMEZONE
# =========================================================


def test_custom_timezone(
    compiler,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
        timezone="America/New_York",
    )

    result = compiler.compile_search(
        request,
        reference=REFERENCE,
    )

    assert result["timeZone"] == (
        "America/New_York"
    )

    assert result["timeMin"].endswith(
        "-04:00"
    )

    assert result["timeMax"].endswith(
        "-04:00"
    )


# =========================================================
# GOOGLE CALENDAR PARAMETERS
# =========================================================


def test_google_calendar_defaults(
    compiler,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="today",
    )

    result = compiler.compile_search(
        request,
        reference=REFERENCE,
    )

    assert result["singleEvents"] is True
    assert result["orderBy"] == "startTime"
    assert result["timeZone"] == "Asia/Kolkata"


# =========================================================
# DATE + TIME
# =========================================================


@pytest.mark.parametrize(
    (
        "date_expression",
        "start_time",
        "end_time",
        "expected_start",
        "expected_end",
    ),
    [
        (
            "tomorrow",
            "07:00",
            "09:00",
            "2026-08-12T07:00:00+05:30",
            "2026-08-12T09:00:00+05:30",
        ),
        (
            "today",
            "09:30",
            "11:45",
            "2026-08-11T09:30:00+05:30",
            "2026-08-11T11:45:00+05:30",
        ),
        (
            "tomorrow",
            "7 AM",
            "9 AM",
            "2026-08-12T07:00:00+05:30",
            "2026-08-12T09:00:00+05:30",
        ),
    ],
)
def test_date_and_time_combinations(
    compiler,
    date_expression,
    start_time,
    end_time,
    expected_start,
    expected_end,
):

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date=date_expression,
        start_time=start_time,
        end_time=end_time,
    )

    result = compiler.compile_search(
        request,
        reference=REFERENCE,
    )

    assert result["timeMin"] == expected_start
    assert result["timeMax"] == expected_end