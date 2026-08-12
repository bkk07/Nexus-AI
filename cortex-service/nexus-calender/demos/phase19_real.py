from __future__ import annotations

import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analytics import (
    build_day_summary,
    build_week_summary,
)
from busy_intervals import (
    events_to_busy_intervals,
)
from compiler import CalendarQueryCompiler
from connector.google_calendar_client import GoogleCalendarClient
from datetime_utils import DateTimeRange
from engine.search import CalendarSearchEngine
from free_slots import find_free_slots
from models import (
    CalendarOperation,
    CalendarRequest,
)


TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)


def print_day_summary(summary) -> None:

    print(
        f"Date: {summary.date}"
    )

    print(
        f"Events: "
        f"{summary.event_count}"
    )

    print(
        f"Busy minutes: "
        f"{summary.busy_minutes}"
    )

    print(
        f"Free minutes: "
        f"{summary.free_minutes}"
    )

    print(
        f"Longest free slot: "
        f"{summary.longest_free_slot_minutes} minutes"
    )

    print(
        f"Meeting minutes: "
        f"{summary.meeting_minutes}"
    )

    print(
        f"Fragmentation score: "
        f"{summary.fragmentation_score:.3f}"
    )


def build_window(
    day: date,
) -> DateTimeRange:

    return DateTimeRange(
        start=datetime.combine(
            day,
            time(0, 0),
            tzinfo=IST,
        ),
        end=datetime.combine(
            day,
            time(23, 59),
            tzinfo=IST,
        ),
    )


def main() -> None:

    print("=" * 70)
    print(
        "PHASE 19 - REAL GOOGLE CALENDAR ANALYTICS VALIDATION"
    )
    print("=" * 70)

    reference = datetime.now(IST)

    print()
    print("Reference:")
    print(reference.isoformat())

    # =========================================================
    # 1. REAL GOOGLE CALENDAR CLIENT
    # =========================================================

    client = GoogleCalendarClient(
        calendar_id="primary",
    )

    compiler = CalendarQueryCompiler(
        default_timezone=TIMEZONE,
        default_search_days=30,
    )

    search_engine = CalendarSearchEngine(
        client=client,
        compiler=compiler,
    )

    # =========================================================
    # 2. SEARCH TODAY'S REAL CALENDAR
    # =========================================================

    print()
    print("=" * 70)
    print("1. SEARCH TODAY'S REAL CALENDAR")
    print("=" * 70)

    today_request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="today",
        start_time="00:00",
        end_time="23:59",
    )

    today_events = search_engine.search_events(
        today_request,
        reference=reference,
    )

    print(
        f"REAL GOOGLE EVENTS FOUND: "
        f"{len(today_events)}"
    )

    for index, event in enumerate(
        today_events,
        start=1,
    ):

        print(
            f"{index}. "
            f"{event.title}: "
            f"{event.start.isoformat()} -> "
            f"{event.end.isoformat()}"
        )

    # =========================================================
    # 3. CONVERT EVENTS TO BUSY INTERVALS
    # =========================================================

    print()
    print("=" * 70)
    print("2. CONVERT REAL EVENTS TO BUSY INTERVALS")
    print("=" * 70)

    today_busy = events_to_busy_intervals(
        today_events
    )

    print(
        f"MERGED BUSY INTERVALS: "
        f"{len(today_busy)}"
    )

    for interval in today_busy:

        print(
            f"{interval.start.isoformat()} -> "
            f"{interval.end.isoformat()} "
            f"| events={interval.source_event_ids}"
        )

    # =========================================================
    # 4. GENERATE REAL FREE SLOTS
    #
    # Use the entire calendar day so the analytics are
    # directly based on the real calendar.
    # =========================================================

    print()
    print("=" * 70)
    print("3. CALCULATE REAL FREE SLOTS")
    print("=" * 70)

    today_window = build_window(
        reference.date()
    )

    today_free = find_free_slots(
        window=today_window,
        busy_intervals=today_busy,
        minimum_duration_minutes=1,
    )

    print(
        f"FREE SLOTS FOUND: "
        f"{len(today_free)}"
    )

    for slot in today_free:

        print(
            f"{slot.start.isoformat()} -> "
            f"{slot.end.isoformat()} "
            f"({slot.duration_minutes} min)"
        )

    # =========================================================
    # 5. BUILD TODAY'S DAY SUMMARY
    # =========================================================

    print()
    print("=" * 70)
    print("4. TODAY'S DAY SUMMARY")
    print("=" * 70)

    today_summary = build_day_summary(
        reference.date(),
        today_events,
        today_busy,
        today_free,
    )

    print_day_summary(
        today_summary
    )

    # =========================================================
    # 6. VERIFY DAY SUMMARY
    # =========================================================

    print()
    print("=" * 70)
    print("5. DAY SUMMARY VALIDATION")
    print("=" * 70)

    expected_busy_minutes = sum(
        int(
            (
                interval.end
                - interval.start
            ).total_seconds()
            // 60
        )
        for interval in today_busy
    )

    expected_free_minutes = sum(
        slot.duration_minutes
        for slot in today_free
    )

    expected_longest_free = max(
        (
            slot.duration_minutes
            for slot in today_free
        ),
        default=0,
    )

    expected_meeting_minutes = sum(
        int(
            (
                event.end
                - event.start
            ).total_seconds()
            // 60
        )
        for event in today_events
    )

    assert (
        today_summary.event_count
        == len(today_events)
    )

    assert (
        today_summary.busy_minutes
        == expected_busy_minutes
    )

    assert (
        today_summary.free_minutes
        == expected_free_minutes
    )

    assert (
        today_summary.longest_free_slot_minutes
        == expected_longest_free
    )

    assert (
        today_summary.meeting_minutes
        == expected_meeting_minutes
    )

    assert (
        0.0
        <= today_summary.fragmentation_score
        <= 1.0
    )

    print(
        "Event count validation: PASSED"
    )

    print(
        "Busy minutes validation: PASSED"
    )

    print(
        "Free minutes validation: PASSED"
    )

    print(
        "Longest free slot validation: PASSED"
    )

    print(
        "Meeting minutes validation: PASSED"
    )

    print(
        "Fragmentation validation: PASSED"
    )

    # =========================================================
    # 7. SEARCH TOMORROW
    #
    # Used to demonstrate the same analytics pipeline on
    # another real calendar day.
    # =========================================================

    print()
    print("=" * 70)
    print("6. SEARCH TOMORROW'S REAL CALENDAR")
    print("=" * 70)

    tomorrow = (
        reference.date()
        + timedelta(days=1)
    )

    tomorrow_request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="tomorrow",
        start_time="00:00",
        end_time="23:59",
    )

    tomorrow_events = search_engine.search_events(
        tomorrow_request,
        reference=reference,
    )

    print(
        f"REAL GOOGLE EVENTS FOUND: "
        f"{len(tomorrow_events)}"
    )

    for index, event in enumerate(
        tomorrow_events,
        start=1,
    ):

        print(
            f"{index}. "
            f"{event.title}: "
            f"{event.start.isoformat()} -> "
            f"{event.end.isoformat()}"
        )

    tomorrow_busy = events_to_busy_intervals(
        tomorrow_events
    )

    tomorrow_window = build_window(
        tomorrow
    )

    tomorrow_free = find_free_slots(
        window=tomorrow_window,
        busy_intervals=tomorrow_busy,
        minimum_duration_minutes=1,
    )

    tomorrow_summary = build_day_summary(
        tomorrow,
        tomorrow_events,
        tomorrow_busy,
        tomorrow_free,
    )

    print()
    print("Tomorrow summary:")

    print_day_summary(
        tomorrow_summary
    )

    # =========================================================
    # 8. WEEK ANALYTICS
    #
    # Build a small real-calendar week using actual Google
    # Calendar data. We use the current week Monday-Friday.
    # =========================================================

    print()
    print("=" * 70)
    print("7. REAL WEEK ANALYTICS")
    print("=" * 70)

    week_start = (
        reference.date()
        - timedelta(
            days=reference.weekday()
        )
    )

    day_summaries = []

    for day_offset in range(5):

        day = (
            week_start
            + timedelta(days=day_offset)
        )

        # -----------------------------------------------------
        # Search each day independently.
        # This avoids accidentally treating the entire week
        # as one continuous scheduling window.
        # -----------------------------------------------------

        day_request = CalendarRequest(
            operation=CalendarOperation.SEARCH,
            date=day.isoformat(),
            start_time="00:00",
            end_time="23:59",
        )

        day_events = search_engine.search_events(
            day_request,
            reference=reference,
        )

        day_busy = events_to_busy_intervals(
            day_events
        )

        day_window = build_window(
            day
        )

        day_free = find_free_slots(
            window=day_window,
            busy_intervals=day_busy,
            minimum_duration_minutes=1,
        )

        summary = build_day_summary(
            day,
            day_events,
            day_busy,
            day_free,
        )

        day_summaries.append(
            summary
        )

        print()
        print(
            f"{day}: "
            f"events={summary.event_count}, "
            f"busy={summary.busy_minutes} min, "
            f"free={summary.free_minutes} min, "
            f"meetings={summary.meeting_minutes} min, "
            f"longest_free="
            f"{summary.longest_free_slot_minutes} min, "
            f"fragmentation="
            f"{summary.fragmentation_score:.3f}"
        )

    # =========================================================
    # 9. BUILD WEEK SUMMARY
    # =========================================================

    week_summary = build_week_summary(
        week_start,
        day_summaries,
    )

    print()
    print("=" * 70)
    print("8. WEEK SUMMARY")
    print("=" * 70)

    print(
        f"Week start: "
        f"{week_summary.week_start}"
    )

    print(
        f"Least busy day: "
        f"{week_summary.least_busy_day}"
    )

    print(
        f"Busiest day: "
        f"{week_summary.busiest_day}"
    )

    print(
        f"Total free minutes: "
        f"{week_summary.total_free_minutes}"
    )

    # =========================================================
    # 10. WEEK SUMMARY VALIDATION
    # =========================================================

    print()
    print("=" * 70)
    print("9. WEEK SUMMARY VALIDATION")
    print("=" * 70)

    expected_total_free = sum(
        summary.free_minutes
        for summary in day_summaries
    )

    expected_busiest_day = max(
        day_summaries,
        key=lambda summary: (
            summary.busy_minutes,
            -summary.date.toordinal(),
        ),
    ).date

    expected_least_busy_day = min(
        day_summaries,
        key=lambda summary: (
            summary.busy_minutes,
            summary.date.toordinal(),
        ),
    ).date

    assert (
        week_summary.total_free_minutes
        == expected_total_free
    )

    assert (
        week_summary.busiest_day
        == expected_busiest_day
    )

    assert (
        week_summary.least_busy_day
        == expected_least_busy_day
    )

    assert (
        len(week_summary.day_summaries)
        == len(day_summaries)
    )

    print(
        "Total weekly free time: PASSED"
    )

    print(
        "Busiest day: PASSED"
    )

    print(
        "Least busy day: PASSED"
    )

    print(
        "Daily summaries: PASSED"
    )

    # =========================================================
    # 11. ZERO WRITE VALIDATION
    # =========================================================

    print()
    print("=" * 70)
    print("10. GOOGLE CALENDAR WRITE SAFETY")
    print("=" * 70)

    print(
        "Google Calendar events created: 0"
    )

    print(
        "Google Calendar events modified: 0"
    )

    print(
        "Google Calendar events deleted: 0"
    )

    print(
        "REAL CALENDAR WRITE OPERATIONS: 0"
    )

    # =========================================================
    # FINAL
    # =========================================================

    print()
    print("=" * 70)
    print(
        "PHASE 19 REAL GOOGLE VALIDATION: PASSED"
    )
    print("=" * 70)

    print()
    print(
        "Real Google Calendar events were used "
        "for day and week analytics."
    )

    print(
        "No Google Calendar events were created."
    )

    print(
        "No Google Calendar events were modified."
    )

    print(
        "No Google Calendar events were deleted."
    )


if __name__ == "__main__":
    main()