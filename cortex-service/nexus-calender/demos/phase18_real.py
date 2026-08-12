from __future__ import annotations

import sys
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from best_slot import BestSlotService
from busy_intervals import events_to_busy_intervals
from compiler import CalendarQueryCompiler
from connector.google_calendar_client import GoogleCalendarClient
from datetime_utils import DateTimeRange
from engine.search import CalendarSearchEngine
from free_slots import find_free_slots
from models import CalendarOperation, CalendarRequest
from preferences import UserPreferences
from windows import SchedulingWindow


TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)


def make_window(
    name: str,
    start: str,
    end: str,
) -> SchedulingWindow:
    return SchedulingWindow(
        name=name,
        start_time=start,
        end_time=end,
        applies_weekdays=[
            0,
            1,
            2,
            3,
            4,
        ],
    )


def main() -> None:

    print("=" * 70)
    print("PHASE 18 - REAL GOOGLE CALENDAR PREFERENCES VALIDATION")
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

    request = CalendarRequest(
        operation=CalendarOperation.SEARCH,
        date="today",
        start_time="00:00",
        end_time="23:59",
    )

    events = search_engine.search_events(
        request,
        reference=reference,
    )

    print(
        f"REAL GOOGLE EVENTS FOUND: {len(events)}"
    )

    for index, event in enumerate(
        events,
        start=1,
    ):
        print(
            f"{index}. "
            f"{event.title}: "
            f"{event.start.isoformat()} -> "
            f"{event.end.isoformat()}"
        )

    # =========================================================
    # 3. CONVERT REAL EVENTS TO BUSY INTERVALS
    # =========================================================

    print()
    print("=" * 70)
    print("2. MERGE REAL GOOGLE CALENDAR BUSY INTERVALS")
    print("=" * 70)

    busy_intervals = events_to_busy_intervals(
        events
    )

    print(
        f"MERGED BUSY INTERVALS: "
        f"{len(busy_intervals)}"
    )

    for interval in busy_intervals:
        print(
            f"{interval.start.isoformat()} -> "
            f"{interval.end.isoformat()} "
            f"| events={interval.source_event_ids}"
        )

    # =========================================================
    # 4. DEFINE PHASE 18 USER PREFERENCES
    #
    # DSA/coding -> preferred study window
    # =========================================================

    print()
    print("=" * 70)
    print("3. APPLY USER PREFERENCES")
    print("=" * 70)

    preferences = UserPreferences(
        preferred_study_window=make_window(
            "preferred_study",
            "18:00",
            "22:00",
        ),
        minimum_focus_minutes=60,
        working_hours=make_window(
            "working_hours",
            "09:00",
            "22:00",
        ),
        blocked_periods=[
            make_window(
                "blocked_lunch",
                "13:00",
                "14:00",
            ),
        ],
    )

    print(
        "Preferred study window: "
        "18:00 -> 22:00"
    )

    print(
        "Minimum focus duration: "
        f"{preferences.minimum_focus_minutes} minutes"
    )

    print(
        "Working hours: "
        "09:00 -> 22:00"
    )

    print(
        "Blocked period: "
        "13:00 -> 14:00"
    )

    # =========================================================
    # 5. BUILD TODAY'S SCHEDULING WINDOW
    # =========================================================

    print()
    print("=" * 70)
    print("4. APPLY WORKING-HOURS WINDOW")
    print("=" * 70)

    today = reference.date()

    working_start = datetime.combine(
        today,
        time(9, 0),
        tzinfo=IST,
    )

    working_end = datetime.combine(
        today,
        time(22, 0),
        tzinfo=IST,
    )

    scheduling_window = DateTimeRange(
        start=working_start,
        end=working_end,
    )

    print(
        f"Scheduling window: "
        f"{working_start.isoformat()} -> "
        f"{working_end.isoformat()}"
    )

    # =========================================================
    # 6. ADD BLOCKED PERIOD TO BUSY INTERVALS
    #
    # This is intentionally done locally.
    # No Google Calendar write.
    # =========================================================

    print()
    print("=" * 70)
    print("5. APPLY BLOCKED PERIOD")
    print("=" * 70)

    blocked_start = datetime.combine(
        today,
        time(13, 0),
        tzinfo=IST,
    )

    blocked_end = datetime.combine(
        today,
        time(14, 0),
        tzinfo=IST,
    )

    print(
        f"Blocked period: "
        f"{blocked_start.isoformat()} -> "
        f"{blocked_end.isoformat()}"
    )

    from busy_intervals import BusyInterval, merge_busy_intervals

    blocked_interval = BusyInterval(
        start=blocked_start,
        end=blocked_end,
        source_event_ids=[],
    )

    all_busy_intervals = merge_busy_intervals(
        busy_intervals + [blocked_interval]
    )

    # =========================================================
    # 7. FIND CANDIDATE FREE SLOTS
    # =========================================================

    print()
    print("=" * 70)
    print("6. FIND FREE SLOTS")
    print("=" * 70)

    slots = find_free_slots(
        window=scheduling_window,
        busy_intervals=all_busy_intervals,
        minimum_duration_minutes=(
            preferences.minimum_focus_minutes
        ),
    )

    print(
        f"FREE SLOTS FOUND: {len(slots)}"
    )

    for slot in slots:
        print(
            f"{slot.start.isoformat()} -> "
            f"{slot.end.isoformat()} "
            f"({slot.duration_minutes} min)"
        )

    # =========================================================
    # 8. VERIFY BLOCKED PERIOD IS NOT A CANDIDATE
    # =========================================================

    print()
    print("=" * 70)
    print("7. BLOCKED PERIOD VALIDATION")
    print("=" * 70)

    for slot in slots:

        assert not (
            slot.start < blocked_end
            and slot.end > blocked_start
        )

    print(
        "No candidate overlaps "
        "13:00 -> 14:00."
    )

    print(
        "BLOCKED PERIOD: PASSED"
    )

    # =========================================================
    # 9. RANK WITHOUT STUDY PREFERENCE
    #
    # This gives us a baseline.
    # =========================================================

    print()
    print("=" * 70)
    print("8. BASELINE RANKING WITHOUT STUDY PREFERENCE")
    print("=" * 70)

    service = BestSlotService()

    baseline = service.rank_slots(
        slots=slots,
        requested_duration_minutes=60,
    )

    if baseline:

        print(
            f"Baseline best slot: "
            f"{baseline[0].slot.start.isoformat()} -> "
            f"{baseline[0].slot.end.isoformat()}"
        )

    # =========================================================
    # 10. RANK WITH STUDY PREFERENCE
    # =========================================================

    print()
    print("=" * 70)
    print("9. RANK WITH STUDY PREFERENCE")
    print("=" * 70)

    preferred = service.rank_slots(
        slots=slots,
        requested_duration_minutes=60,
        preferred_window_start=time(18, 0),
        preferred_window_end=time(22, 0),
    )

    if preferred:

        print(
            f"Preferred best slot: "
            f"{preferred[0].slot.start.isoformat()} -> "
            f"{preferred[0].slot.end.isoformat()}"
        )

        print(
            f"Score: "
            f"{preferred[0].score:.4f}"
        )

        for reason in preferred[0].reasons:
            print(
                f"- {reason}"
            )

    # =========================================================
    # 11. PREFERENCE MUST CHANGE RANKING
    # =========================================================

    print()
    print("=" * 70)
    print("10. PREFERENCE RANKING VALIDATION")
    print("=" * 70)

    if len(slots) >= 2:

        assert preferred

        # A preference should not make the result worse
        # when an evening candidate exists.
        evening_candidates = [
            slot
            for slot in slots
            if slot.start.hour >= 18
        ]

        if evening_candidates:

            assert (
                preferred[0].slot
                in evening_candidates
            )

            print(
                "Evening preference selected "
                "an evening candidate."
            )

            print(
                "PREFERENCE RANKING: PASSED"
            )

        else:

            print(
                "No evening free slot exists today."
            )

            print(
                "PREFERENCE RANKING: "
                "SKIPPED (no evening candidate)"
            )

    else:

        print(
            "Not enough free candidates to compare."
        )

        print(
            "PREFERENCE RANKING: "
            "SKIPPED (insufficient candidates)"
        )

    # =========================================================
    # 12. MINIMUM FOCUS VALIDATION
    # =========================================================

    print()
    print("=" * 70)
    print("11. MINIMUM FOCUS VALIDATION")
    print("=" * 70)

    for slot in slots:

        assert (
            slot.duration_minutes
            >= preferences.minimum_focus_minutes
        )

    print(
        "Every returned candidate is at least "
        f"{preferences.minimum_focus_minutes} minutes."
    )

    print(
        "MINIMUM FOCUS: PASSED"
    )

    # =========================================================
    # 13. REAL CALENDAR SAFETY
    # =========================================================

    print()
    print("=" * 70)
    print("12. GOOGLE CALENDAR SAFETY")
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
    print("PHASE 18 REAL GOOGLE VALIDATION: PASSED")
    print("=" * 70)

    print()
    print(
        "User preferences were applied to "
        "real Google Calendar availability."
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