from datetime import datetime

import pytest

from availability_service import AvailabilityService
from busy_intervals import BusyInterval
from models import CalendarOperation, CalendarRequest


REFERENCE = datetime(
    2026,
    8,
    11,
    10,
    0,
)


def busy(
    start_hour: int,
    end_hour: int,
    event_id: str,
) -> BusyInterval:

    from datetime_utils import DateTimeNormalizer

    normalizer = DateTimeNormalizer(
        timezone="Asia/Kolkata"
    )

    start = normalizer._ensure_timezone(
        datetime(
            2026,
            8,
            12,
            start_hour,
        )
    )

    end = normalizer._ensure_timezone(
        datetime(
            2026,
            8,
            12,
            end_hour,
        )
    )

    return BusyInterval(
        start=start,
        end=end,
        source_event_ids=[event_id],
    )


def test_free_time_tomorrow():

    service = AvailabilityService()

    request = CalendarRequest(
        operation=CalendarOperation.CHECK_AVAILABILITY,
        date="tomorrow",
        start_time="12:00",
        end_time="13:00",
    )

    result = service.check(
        request,
        [
            busy(9, 10, "event-1"),
            busy(14, 16, "event-2"),
        ],
        reference=REFERENCE,
    )

    assert result.available is True
    assert result.conflicts == []


def test_busy_time_tomorrow():

    service = AvailabilityService()

    request = CalendarRequest(
        operation=CalendarOperation.CHECK_AVAILABILITY,
        date="tomorrow",
        start_time="10:00",
        end_time="11:00",
    )

    result = service.check(
        request,
        [
            busy(9, 12, "event-1"),
        ],
        reference=REFERENCE,
    )

    assert result.available is False
    assert len(result.conflicts) == 1
    assert (
        result.conflicts[0].source_event_ids
        == ["event-1"]
    )


def test_partial_overlap_is_busy():

    service = AvailabilityService()

    request = CalendarRequest(
        operation=CalendarOperation.CHECK_AVAILABILITY,
        date="tomorrow",
        start_time="11:00",
        end_time="13:00",
    )

    result = service.check(
        request,
        [
            busy(12, 14, "event-1"),
        ],
        reference=REFERENCE,
    )

    assert result.available is False


def test_boundary_touching_is_free():

    service = AvailabilityService()

    request = CalendarRequest(
        operation=CalendarOperation.CHECK_AVAILABILITY,
        date="tomorrow",
        start_time="12:00",
        end_time="13:00",
    )

    result = service.check(
        request,
        [
            busy(9, 12, "event-1"),
            busy(13, 15, "event-2"),
        ],
        reference=REFERENCE,
    )

    assert result.available is True
    assert result.conflicts == []


def test_multiple_conflicts():

    service = AvailabilityService()

    request = CalendarRequest(
        operation=CalendarOperation.CHECK_AVAILABILITY,
        date="tomorrow",
        start_time="10:00",
        end_time="15:00",
    )

    result = service.check(
        request,
        [
            busy(9, 11, "event-1"),
            busy(12, 13, "event-2"),
            busy(14, 16, "event-3"),
        ],
        reference=REFERENCE,
    )

    assert result.available is False
    assert len(result.conflicts) == 3


def test_missing_date_is_rejected():

    service = AvailabilityService()

    request = CalendarRequest(
        operation=CalendarOperation.CHECK_AVAILABILITY,
        start_time="10:00",
        end_time="11:00",
    )

    with pytest.raises(ValueError):
        service.check(
            request,
            [],
            reference=REFERENCE,
        )


def test_missing_start_time_is_rejected():

    service = AvailabilityService()

    request = CalendarRequest(
        operation=CalendarOperation.CHECK_AVAILABILITY,
        date="tomorrow",
        end_time="11:00",
    )

    with pytest.raises(ValueError):
        service.check(
            request,
            [],
            reference=REFERENCE,
        )


def test_missing_end_time_is_rejected():

    service = AvailabilityService()

    request = CalendarRequest(
        operation=CalendarOperation.CHECK_AVAILABILITY,
        date="tomorrow",
        start_time="10:00",
    )

    with pytest.raises(ValueError):
        service.check(
            request,
            [],
            reference=REFERENCE,
        )


def test_wrong_operation_is_rejected():

    service = AvailabilityService()

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
        start_time="10:00",
        end_time="11:00",
    )

    with pytest.raises(ValueError):
        service.check(
            request,
            [],
            reference=REFERENCE,
        )