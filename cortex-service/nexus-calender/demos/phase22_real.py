from __future__ import annotations

import sys

from datetime import date, datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from analytics import build_day_summary
from busy_intervals import (
    events_to_busy_intervals,
    merge_busy_intervals,
)
from connector.google_calendar_client import (
    GoogleCalendarClient,
)
from datetime_utils import DateTimeRange
from engine.habits import (
    HabitDefinition,
    propose_habit_schedule,
)
from free_slots import find_free_slots


TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)


START_DATE = date(
    2026,
    8,
    10,
)

END_DATE = date(
    2026,
    8,
    14,
)


def day_range(
    target_date: date,
) -> DateTimeRange:

    start = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        9,
        0,
        tzinfo=IST,
    )

    end = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        22,
        0,
        tzinfo=IST,
    )

    return DateTimeRange(
        start=start,
        end=end,
    )


def search_day(
    client: GoogleCalendarClient,
    target_date: date,
):
    window = day_range(
        target_date,
    )

    events = client.search(
        {
            "timeMin": window.start.isoformat(),
            "timeMax": window.end.isoformat(),
            "singleEvents": True,
            "orderBy": "startTime",
        }
    )

    return events


def print_events(
    events,
) -> None:

    if not events:
        print(
            "   REAL GOOGLE EVENTS FOUND: 0"
        )
        return

    print(
        f"   REAL GOOGLE EVENTS FOUND: "
        f"{len(events)}"
    )

    for event in events:

        print(
            f"   - {event.title}: "
            f"{event.start.isoformat()} "
            f"-> "
            f"{event.end.isoformat()}"
        )


def build_free_slots_for_day(
    events,
    target_date: date,
):

    window = day_range(
        target_date,
    )

    busy = events_to_busy_intervals(
        events,
    )

    merged = merge_busy_intervals(
        busy,
    )

    free_slots = find_free_slots(
        window=window,
        busy_intervals=merged,
        minimum_duration_minutes=1,
    )

    return merged, free_slots


def main() -> None:

    reference = datetime.now(
        IST,
    )

    print()
    print(
        "# PHASE 22 - REAL GOOGLE CALENDAR "
        "RECURRING HABIT VALIDATION"
    )

    print()
    print(
        f"Reference: {reference.isoformat()}"
    )

    print()
    print("=" * 70)

    print()
    print("1. INITIALIZE REAL GOOGLE CALENDAR")

    client = GoogleCalendarClient()

    print(
        "   REAL GOOGLE CALENDAR CLIENT: READY"
    )

    print()
    print("2. HABIT REQUEST")

    habit = HabitDefinition(
        title="NEXUS AI DSA",
        duration_minutes=120,
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
        preferred_window_start=time(
            18,
            0,
        ),
        preferred_window_end=time(
            22,
            0,
        ),
        start_date=START_DATE,
        end_date=END_DATE,
    )

    print(
        f"   Habit: {habit.title}"
    )

    print(
        f"   Duration: "
        f"{habit.duration_minutes} minutes"
    )

    print(
        "   Applies: Monday -> Friday"
    )

    print(
        "   Preferred window: "
        "18:00 -> 22:00"
    )

    print(
        f"   Date range: "
        f"{habit.start_date} -> "
        f"{habit.end_date}"
    )

    available_slots_by_date = {}

    print()
    print(
        "3. SEARCH REAL GOOGLE CALENDAR "
        "FOR EACH HABIT DAY"
    )

    current_date = START_DATE

    while current_date <= END_DATE:

        if (
            current_date.weekday()
            not in habit.applies_weekdays
        ):
            current_date += timedelta(
                days=1,
            )
            continue

        print()
        print(
            f"DATE: {current_date}"
        )

        events = search_day(
            client,
            current_date,
        )

        print_events(
            events,
        )

        merged, free_slots = (
            build_free_slots_for_day(
                events,
                current_date,
            )
        )

        print(
            f"   MERGED BUSY INTERVALS: "
            f"{len(merged)}"
        )

        for interval in merged:
            print(
                f"   BUSY: "
                f"{interval.start.isoformat()} "
                f"-> "
                f"{interval.end.isoformat()}"
            )

        print(
            f"   FREE SLOTS: "
            f"{len(free_slots)}"
        )

        for slot in free_slots:
            print(
                f"   FREE: "
                f"{slot.start.isoformat()} "
                f"-> "
                f"{slot.end.isoformat()} "
                f"({slot.duration_minutes} min)"
            )

        available_slots_by_date[
            current_date
        ] = free_slots

        current_date += timedelta(
            days=1,
        )

    print()
    print(
        "4. RUN PHASE 22 RECURRING HABIT "
        "SCHEDULER"
    )

    result = propose_habit_schedule(
        habit,
        available_slots_by_date,
    )

    print()

    print(
        f"TOTAL APPLICABLE DAYS: "
        f"{result.total_applicable_days}"
    )

    print(
        f"SCHEDULED DAYS: "
        f"{result.scheduled_days}"
    )

    print(
        f"UNSCHEDULED DAYS: "
        f"{result.unscheduled_days}"
    )

    print(
        f"SUMMARY: "
        f"{result.summary}"
    )

    print()
    print(
        "5. DAILY RESULTS"
    )

    for day_result in result.days:

        print()
        print(
            f"{day_result.date}:"
        )

        if not day_result.scheduled:

            print(
                "   STATUS: UNSCHEDULED"
            )

            print(
                "   Reason: "
                "no viable slot"
            )

            continue

        print(
            "   STATUS: SCHEDULED"
        )

        print(
            f"   BLOCK: "
            f"{day_result.slot.start.isoformat()} "
            f"-> "
            f"{day_result.slot.end.isoformat()}"
        )

        print(
            f"   DURATION: "
            f"{day_result.slot.duration_minutes} min"
        )

        if day_result.score is not None:
            print(
                f"   SCORE: "
                f"{day_result.score:.4f}"
            )

        for reason in day_result.reasons:
            print(
                f"   - {reason}"
            )

    print()
    print(
        "6. VALIDATION"
    )

    all_days_accounted_for = (
        result.total_applicable_days
        == len(result.days)
    )

    no_weekend_days = all(
        day.date.weekday() in (
            habit.applies_weekdays
        )
        for day in result.days
    )

    all_durations_valid = all(
        (
            not day.scheduled
            or (
                day.slot is not None
                and day.slot.duration_minutes
                >= habit.duration_minutes
            )
        )
        for day in result.days
    )

    all_inside_preferred_window = all(
        (
            not day.scheduled
            or (
                day.slot is not None
                and day.slot.start.time()
                >= habit.preferred_window_start
                and day.slot.end.time()
                <= habit.preferred_window_end
            )
        )
        for day in result.days
    )

    print(
        "   EVERY APPLICABLE DAY ACCOUNTED FOR: "
        + (
            "PASSED"
            if all_days_accounted_for
            else "FAILED"
        )
    )

    print(
        "   WEEKDAY VALIDATION: "
        + (
            "PASSED"
            if no_weekend_days
            else "FAILED"
        )
    )

    print(
        "   DURATION VALIDATION: "
        + (
            "PASSED"
            if all_durations_valid
            else "FAILED"
        )
    )

    print(
        "   PREFERRED WINDOW VALIDATION: "
        + (
            "PASSED"
            if all_inside_preferred_window
            else "FAILED"
        )
    )

    print()
    print(
        "7. REAL CALENDAR WRITE OPERATIONS"
    )

    print(
        "   Google Calendar events created: 0"
    )

    print(
        "   Google Calendar events modified: 0"
    )

    print(
        "   Google Calendar events deleted: 0"
    )

    print(
        "   REAL CALENDAR WRITE OPERATIONS: 0"
    )

    print()
    print("=" * 70)

    if (
        all_days_accounted_for
        and no_weekend_days
        and all_durations_valid
        and all_inside_preferred_window
    ):
        print(
            "PHASE 22 RECURRING HABIT VALIDATION: "
            "PASSED"
        )
    else:
        print(
            "PHASE 22 RECURRING HABIT VALIDATION: "
            "FAILED"
        )

    print()
    print(
        "Real Google Calendar events were used "
        "as scheduling constraints."
    )

    print(
        "Recurring habit scheduling was performed "
        "independently for each applicable day."
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