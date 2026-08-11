from datetime import datetime

from availability import check_availability
from busy_intervals import BusyInterval
from datetime_utils import DateTimeRange


def dt(
    hour: int,
    minute: int = 0,
) -> datetime:
    return datetime(
        2026,
        8,
        12,
        hour,
        minute,
    ).astimezone()


def make_range(
    start_hour: int,
    start_minute: int,
    end_hour: int,
    end_minute: int,
) -> DateTimeRange:

    return DateTimeRange(
        start=dt(
            start_hour,
            start_minute,
        ),
        end=dt(
            end_hour,
            end_minute,
        ),
    )


def make_busy(
    start_hour: int,
    start_minute: int,
    end_hour: int,
    end_minute: int,
    event_id: str,
) -> BusyInterval:

    return BusyInterval(
        start=dt(
            start_hour,
            start_minute,
        ),
        end=dt(
            end_hour,
            end_minute,
        ),
        source_event_ids=[event_id],
    )


def test_fully_free_window():

    requested = make_range(
        9,
        0,
        10,
        0,
    )

    result = check_availability(
        requested,
        [],
    )

    assert result.available is True
    assert result.conflicts == []

    assert result.requested_range == requested


def test_fully_occupied_window():

    requested = make_range(
        10,
        0,
        11,
        0,
    )

    busy = [
        make_busy(
            9,
            0,
            12,
            0,
            "event-1",
        )
    ]

    result = check_availability(
        requested,
        busy,
    )

    assert result.available is False
    assert result.conflicts == busy


def test_partial_overlap_at_start():

    requested = make_range(
        10,
        0,
        12,
        0,
    )

    busy = [
        make_busy(
            9,
            0,
            11,
            0,
            "event-1",
        )
    ]

    result = check_availability(
        requested,
        busy,
    )

    assert result.available is False
    assert result.conflicts == busy


def test_partial_overlap_at_end():

    requested = make_range(
        10,
        0,
        12,
        0,
    )

    busy = [
        make_busy(
            11,
            0,
            13,
            0,
            "event-1",
        )
    ]

    result = check_availability(
        requested,
        busy,
    )

    assert result.available is False
    assert result.conflicts == busy


def test_exact_overlap():

    requested = make_range(
        10,
        0,
        12,
        0,
    )

    busy = [
        make_busy(
            10,
            0,
            12,
            0,
            "event-1",
        )
    ]

    result = check_availability(
        requested,
        busy,
    )

    assert result.available is False
    assert result.conflicts == busy


def test_multiple_conflicts_are_all_returned():

    requested = make_range(
        10,
        0,
        14,
        0,
    )

    busy = [
        make_busy(
            9,
            0,
            11,
            0,
            "event-1",
        ),
        make_busy(
            10,
            0,
            12,
            0,
            "event-2",
        ),
        make_busy(
            13,
            0,
            15,
            0,
            "event-3",
        ),
    ]

    result = check_availability(
        requested,
        busy,
    )

    assert result.available is False
    assert len(result.conflicts) == 3
    assert result.conflicts == busy


def test_boundary_touching_at_start_is_available():

    requested = make_range(
        11,
        0,
        12,
        0,
    )

    busy = [
        make_busy(
            10,
            0,
            11,
            0,
            "event-1",
        )
    ]

    result = check_availability(
        requested,
        busy,
    )

    assert result.available is True
    assert result.conflicts == []


def test_boundary_touching_at_end_is_available():

    requested = make_range(
        10,
        0,
        11,
        0,
    )

    busy = [
        make_busy(
            11,
            0,
            12,
            0,
            "event-1",
        )
    ]

    result = check_availability(
        requested,
        busy,
    )

    assert result.available is True
    assert result.conflicts == []


def test_requested_range_inside_busy_interval():

    requested = make_range(
        10,
        0,
        11,
        0,
    )

    busy = [
        make_busy(
            9,
            0,
            12,
            0,
            "event-1",
        )
    ]

    result = check_availability(
        requested,
        busy,
    )

    assert result.available is False
    assert result.conflicts == busy


def test_busy_interval_inside_requested_range():

    requested = make_range(
        9,
        0,
        13,
        0,
    )

    busy = [
        make_busy(
            10,
            0,
            11,
            0,
            "event-1",
        )
    ]

    result = check_availability(
        requested,
        busy,
    )

    assert result.available is False
    assert result.conflicts == busy


def test_overnight_requested_range():

    requested = DateTimeRange(
        start=dt(23, 0),
        end=datetime(
            2026,
            8,
            13,
            2,
            0,
        ).astimezone(),
    )

    busy = [
        BusyInterval(
            start=datetime(
                2026,
                8,
                13,
                0,
                0,
            ).astimezone(),
            end=datetime(
                2026,
                8,
                13,
                1,
                0,
            ).astimezone(),
            source_event_ids=["event-1"],
        )
    ]

    result = check_availability(
        requested,
        busy,
    )

    assert result.available is False
    assert result.conflicts == busy