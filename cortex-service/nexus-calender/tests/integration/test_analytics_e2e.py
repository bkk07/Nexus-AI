from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from analytics import (
    build_day_summary,
    build_week_summary,
)
from busy_intervals import (
    BusyInterval,
    merge_busy_intervals,
)
from datetime_utils import DateTimeRange
from free_slots import find_free_slots
from models import EventSummary


IST = ZoneInfo("Asia/Kolkata")


def dt(
    day: date,
    hour: int,
    minute: int = 0,
) -> datetime:

    return datetime(
        day.year,
        day.month,
        day.day,
        hour,
        minute,
        tzinfo=IST,
    )


def make_event(
    event_id: str,
    day: date,
    start_hour: int,
    end_hour: int,
    title: str = "Meeting",
) -> EventSummary:

    return EventSummary(
        event_id=event_id,
        title=title,
        start=dt(day, start_hour),
        end=dt(day, end_hour),
    )


def make_busy(
    event: EventSummary,
) -> BusyInterval:

    return BusyInterval(
        start=event.start,
        end=event.end,
        source_event_ids=[
            event.event_id,
        ],
    )


def build_day_data(
    day: date,
    events: list[EventSummary],
) -> tuple[
    list[BusyInterval],
    list,
]:

    busy = [
        make_busy(event)
        for event in events
    ]

    merged_busy = merge_busy_intervals(
        busy
    )

    window = DateTimeRange(
        start=dt(day, 9),
        end=dt(day, 18),
    )

    free_slots = find_free_slots(
        window=window,
        busy_intervals=merged_busy,
        minimum_duration_minutes=1,
    )

    return merged_busy, free_slots


# =========================================================
# TEST 1
# "How busy am I tomorrow?"
#
# Reference day:
# 2026-08-11
#
# Tomorrow:
# 2026-08-12
# =========================================================

def test_how_busy_am_i_tomorrow():

    reference = date(
        2026,
        8,
        11,
    )

    tomorrow = reference + timedelta(
        days=1
    )

    events = [
        make_event(
            "tomorrow-1",
            tomorrow,
            9,
            10,
        ),
        make_event(
            "tomorrow-2",
            tomorrow,
            14,
            16,
        ),
    ]

    busy, free = build_day_data(
        tomorrow,
        events,
    )

    summary = build_day_summary(
        tomorrow,
        events,
        busy,
        free,
    )

    assert summary.date == tomorrow

    assert summary.event_count == 2

    assert summary.busy_minutes == 180

    assert summary.meeting_minutes == 180

    assert summary.free_minutes == 360

    assert (
        summary.longest_free_slot_minutes
        == 240
    )


# =========================================================
# TEST 2
# "Which day is least busy this week?"
# =========================================================

def test_which_day_is_least_busy_this_week():

    week_start = date(
        2026,
        8,
        10,
    )

    monday = week_start
    tuesday = week_start + timedelta(days=1)
    wednesday = week_start + timedelta(days=2)

    monday_events = [
        make_event(
            "mon-1",
            monday,
            9,
            10,
        ),
    ]

    tuesday_events = [
        make_event(
            "tue-1",
            tuesday,
            9,
            11,
        ),
        make_event(
            "tue-2",
            tuesday,
            14,
            16,
        ),
    ]

    wednesday_events = [
        make_event(
            "wed-1",
            wednesday,
            10,
            11,
        ),
    ]

    monday_busy, monday_free = build_day_data(
        monday,
        monday_events,
    )

    tuesday_busy, tuesday_free = build_day_data(
        tuesday,
        tuesday_events,
    )

    wednesday_busy, wednesday_free = build_day_data(
        wednesday,
        wednesday_events,
    )

    summaries = [
        build_day_summary(
            monday,
            monday_events,
            monday_busy,
            monday_free,
        ),
        build_day_summary(
            tuesday,
            tuesday_events,
            tuesday_busy,
            tuesday_free,
        ),
        build_day_summary(
            wednesday,
            wednesday_events,
            wednesday_busy,
            wednesday_free,
        ),
    ]

    week = build_week_summary(
        week_start,
        summaries,
    )

    assert (
        week.least_busy_day
        == monday
    )

    assert (
        week.busiest_day
        == tuesday
    )


# =========================================================
# TEST 3
# "How many hours am I in meetings?"
# =========================================================

def test_how_many_hours_am_i_in_meetings():

    day = date(
        2026,
        8,
        12,
    )

    events = [
        make_event(
            "meeting-1",
            day,
            9,
            10,
        ),
        make_event(
            "meeting-2",
            day,
            11,
            13,
        ),
        make_event(
            "meeting-3",
            day,
            15,
            16,
        ),
    ]

    busy, free = build_day_data(
        day,
        events,
    )

    summary = build_day_summary(
        day,
        events,
        busy,
        free,
    )

    # 1 + 2 + 1 = 4 hours
    assert summary.meeting_minutes == 240

    assert (
        summary.meeting_minutes / 60
        == 4
    )


# =========================================================
# TEST 4
# "How much free time do I have this week?"
# =========================================================

def test_how_much_free_time_do_i_have_this_week():

    week_start = date(
        2026,
        8,
        10,
    )

    summaries = []

    # Monday
    monday = week_start

    monday_events = [
        make_event(
            "mon-1",
            monday,
            9,
            10,
        ),
    ]

    monday_busy, monday_free = build_day_data(
        monday,
        monday_events,
    )

    summaries.append(
        build_day_summary(
            monday,
            monday_events,
            monday_busy,
            monday_free,
        )
    )

    # Tuesday
    tuesday = week_start + timedelta(
        days=1
    )

    tuesday_events = [
        make_event(
            "tue-1",
            tuesday,
            9,
            11,
        ),
        make_event(
            "tue-2",
            tuesday,
            14,
            16,
        ),
    ]

    tuesday_busy, tuesday_free = build_day_data(
        tuesday,
        tuesday_events,
    )

    summaries.append(
        build_day_summary(
            tuesday,
            tuesday_events,
            tuesday_busy,
            tuesday_free,
        )
    )

    # Wednesday
    wednesday = week_start + timedelta(
        days=2
    )

    wednesday_events = []

    wednesday_busy, wednesday_free = build_day_data(
        wednesday,
        wednesday_events,
    )

    summaries.append(
        build_day_summary(
            wednesday,
            wednesday_events,
            wednesday_busy,
            wednesday_free,
        )
    )

    week = build_week_summary(
        week_start,
        summaries,
    )

    # Monday:
    # 9-10 busy
    # 10-18 free = 480
    #
    # Tuesday:
    # 9-11 busy
    # 14-16 busy
    # 11-14 free = 180
    # 16-18 free = 120
    # total = 300
    #
    # Wednesday:
    # 9-18 completely free = 540
    #
    # Total = 480 + 300 + 540 = 1320

    assert week.total_free_minutes == 1320

    assert (
        week.total_free_minutes / 60
        == 22
    )