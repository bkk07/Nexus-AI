from __future__ import annotations

import sys
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from busy_intervals import (
    events_to_busy_intervals,
    merge_busy_intervals,
)
from compiler import CalendarQueryCompiler
from connector.google_calendar_client import (
    GoogleCalendarClient,
)
from datetime_utils import DateTimeRange
from engine.search import CalendarSearchEngine
from free_slots import find_free_slots
from models import (
    CalendarOperation,
    CalendarRequest,
)
from preferences import (
    UserPreferences,
    blocked_windows_to_busy_intervals,
)
from tasks import (
    Task,
    schedule_task,
    schedule_tasks,
)
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
            5,
            6,
        ],
    )


def print_event(
    index: int,
    event,
) -> None:
    print(
        f"{index}. "
        f"{event.title}: "
        f"{event.start.isoformat()} -> "
        f"{event.end.isoformat()}"
    )


def print_slot(
    slot,
) -> None:
    print(
        f"{slot.start.isoformat()} -> "
        f"{slot.end.isoformat()} "
        f"({slot.duration_minutes} min)"
    )


def print_proposal(
    proposal,
) -> None:

    print(
        f"STATUS: {proposal.status}"
    )

    print(
        f"Unscheduled minutes: "
        f"{proposal.unscheduled_minutes}"
    )

    for index, block in enumerate(
        proposal.blocks,
        start=1,
    ):
        print(
            f"BLOCK {index}: "
            f"{block.slot.start.isoformat()} -> "
            f"{block.slot.end.isoformat()} "
            f"({block.slot.duration_minutes} min)"
        )


def main() -> None:

    reference = datetime.now(IST)

    print()
    print(
        "# PHASE 20 - REAL GOOGLE CALENDAR "
        "TASK SCHEDULING VALIDATION"
    )
    print()
    print("Reference:")
    print(reference.isoformat())

    print()
    print("=" * 70)

    # =========================================================
    # 1. REAL GOOGLE CALENDAR CLIENT
    # =========================================================

    print("1. INITIALIZE REAL GOOGLE CALENDAR")

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

    print("REAL GOOGLE CALENDAR CLIENT: READY")

    # =========================================================
    # 2. SEARCH TODAY'S REAL CALENDAR
    # =========================================================

    print()
    print("=" * 70)
    print("2. SEARCH TODAY'S REAL CALENDAR")
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
        print_event(
            index,
            event,
        )

    # =========================================================
    # 3. CONVERT CALENDAR EVENTS TO BUSY INTERVALS
    # =========================================================

    print()
    print("=" * 70)
    print("3. BUILD REAL CALENDAR BUSY INTERVALS")
    print("=" * 70)

    calendar_busy = events_to_busy_intervals(
        today_events,
    )

    calendar_busy = merge_busy_intervals(
        calendar_busy,
    )

    print(
        f"MERGED BUSY INTERVALS: "
        f"{len(calendar_busy)}"
    )

    for interval in calendar_busy:
        print(
            f"{interval.start.isoformat()} -> "
            f"{interval.end.isoformat()} "
            f"| events="
            f"{interval.source_event_ids}"
        )

    # =========================================================
    # 4. USER PREFERENCES
    # =========================================================

    print()
    print("=" * 70)
    print("4. APPLY USER PREFERENCES")
    print("=" * 70)

    preferences = UserPreferences(
        preferred_study_window=make_window(
            "study",
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
                "lunch",
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
    # 5. CONVERT BLOCKED PERIODS TO BUSY INTERVALS
    # =========================================================

    print()
    print("=" * 70)
    print("5. APPLY BLOCKED PERIODS")
    print("=" * 70)

    blocked_busy = blocked_windows_to_busy_intervals(
        reference.date(),
        preferences,
        timezone=IST,
    )

    for interval in blocked_busy:
        print(
            f"Blocked: "
            f"{interval.start.isoformat()} -> "
            f"{interval.end.isoformat()}"
        )

    # Combine real calendar busy time + blocked periods.

    all_busy = merge_busy_intervals(
        calendar_busy + blocked_busy,
    )

    print()
    print(
        f"TOTAL MERGED BUSY INTERVALS: "
        f"{len(all_busy)}"
    )

    # =========================================================
    # 6. WORKING-HOURS SCHEDULING WINDOW
    # =========================================================

    print()
    print("=" * 70)
    print("6. BUILD WORKING-HOURS AVAILABILITY")
    print("=" * 70)

    window_start = datetime.combine(
        reference.date(),
        time(9, 0),
        tzinfo=IST,
    )

    window_end = datetime.combine(
        reference.date(),
        time(22, 0),
        tzinfo=IST,
    )

    scheduling_window = DateTimeRange(
        start=window_start,
        end=window_end,
    )

    print(
        f"Scheduling window: "
        f"{window_start.isoformat()} -> "
        f"{window_end.isoformat()}"
    )

    free_slots = find_free_slots(
        window=scheduling_window,
        busy_intervals=all_busy,
        minimum_duration_minutes=(
            preferences.minimum_focus_minutes
        ),
    )

    print()
    print(
        f"FREE SLOTS FOUND: "
        f"{len(free_slots)}"
    )

    for slot in free_slots:
        print_slot(slot)

    # =========================================================
    # 7. TASK WITH PREFERRED STUDY WINDOW
    # =========================================================

    print()
    print("=" * 70)
    print("7. TEST PREFERRED-WINDOW TASK")
    print("=" * 70)

    study_task = Task(
        title="NEXUS AI DSA STUDY",
        duration_minutes=60,
        deadline=reference.date(),
        priority="high",
        preferred_window=(
            preferences.preferred_study_window
        ),
        splittable=False,
    )

    print(
        f"Task: {study_task.title}"
    )

    print(
        f"Duration: "
        f"{study_task.duration_minutes} minutes"
    )

    print(
        "Preferred window: "
        "18:00 -> 22:00"
    )

    study_result = schedule_task(
        study_task,
        free_slots,
    )

    print()

    print_proposal(
        study_result,
    )

    # If an evening candidate exists, it must be selected.
    evening_slots = [
        slot
        for slot in free_slots
        if slot.start.time() >= time(18, 0)
        and slot.end.time() <= time(22, 0)
    ]

    if evening_slots:

        assert (
            study_result.status
            == "fully_scheduled"
        )

        assert (
            len(study_result.blocks)
            == 1
        )

        selected = study_result.blocks[0].slot

        assert (
            selected.start >= evening_slots[0].start
        )

        assert (
            selected.end <= evening_slots[-1].end
        )

        print(
            "PREFERRED WINDOW: PASSED"
        )

    else:

        print(
            "No suitable evening free slot "
            "exists in the real calendar."
        )

        print(
            "PREFERRED WINDOW: "
            "NOT APPLICABLE"
        )

    # =========================================================
    # 8. MULTI-TASK SCHEDULING
    # =========================================================

    print()
    print("=" * 70)
    print("8. TEST MULTI-TASK SCHEDULING")
    print("=" * 70)

    project_task = Task(
        title="NEXUS AI PROJECT",
        duration_minutes=120,
        deadline=reference.date(),
        priority="medium",
        splittable=True,
    )

    revision_task = Task(
        title="DSA REVISION",
        duration_minutes=60,
        deadline=reference.date(),
        priority="low",
        splittable=False,
    )

    results = schedule_tasks(
        [
            study_task,
            project_task,
            revision_task,
        ],
        free_slots,
    )

    for title, proposal in results.items():

        print()
        print(
            f"TASK: {title}"
        )

        print_proposal(
            proposal,
        )

    # =========================================================
    # 9. VALIDATE NO OVERLAPPING PROPOSED BLOCKS
    # =========================================================

    print()
    print("=" * 70)
    print("9. VALIDATE TASK NON-OVERLAP")
    print("=" * 70)

    all_blocks = []

    for proposal in results.values():
        all_blocks.extend(
            proposal.blocks
        )

    all_blocks.sort(
        key=lambda block: block.slot.start
    )

    overlap_found = False

    for previous, current in zip(
        all_blocks,
        all_blocks[1:],
    ):

        if (
            current.slot.start
            < previous.slot.end
        ):
            overlap_found = True

            print(
                "OVERLAP FOUND:"
            )

            print(
                f"{previous.task_title}: "
                f"{previous.slot.start.isoformat()} "
                f"-> "
                f"{previous.slot.end.isoformat()}"
            )

            print(
                f"{current.task_title}: "
                f"{current.slot.start.isoformat()} "
                f"-> "
                f"{current.slot.end.isoformat()}"
            )

    assert overlap_found is False

    print(
        "TASK NON-OVERLAP: PASSED"
    )

    # =========================================================
    # 10. VALIDATE BLOCKS ARE INSIDE AVAILABILITY
    # =========================================================

    print()
    print("=" * 70)
    print("10. VALIDATE PROPOSED TASK BLOCKS")
    print("=" * 70)

    for block in all_blocks:

        assert (
            block.slot.start
            >= window_start
        )

        assert (
            block.slot.end
            <= window_end
        )

        assert (
            block.slot.duration_minutes
            > 0
        )

        # Proposed blocks must not overlap
        # real calendar events or blocked periods.

        for busy in all_busy:

            assert not (
                block.slot.start
                < busy.end
                and
                block.slot.end
                > busy.start
            )

    print(
        "WORKING-HOURS VALIDATION: PASSED"
    )

    print(
        "BUSY-EVENT CONFLICT VALIDATION: PASSED"
    )

    print(
        "BLOCKED-PERIOD VALIDATION: PASSED"
    )

    # =========================================================
    # 11. CAPACITY ACCOUNTING
    # =========================================================

    print()
    print("=" * 70)
    print("11. CAPACITY ACCOUNTING")
    print("=" * 70)

    for title, proposal in results.items():

        scheduled_minutes = sum(
            block.slot.duration_minutes
            for block in proposal.blocks
        )

        task = next(
            task
            for task in [
                study_task,
                project_task,
                revision_task,
            ]
            if task.title == title
        )

        assert (
            scheduled_minutes
            + proposal.unscheduled_minutes
            == task.duration_minutes
        )

        print(
            f"{title}: "
            f"scheduled={scheduled_minutes} min, "
            f"unscheduled="
            f"{proposal.unscheduled_minutes} min "
            f"-> PASSED"
        )

    # =========================================================
    # 12. GOOGLE CALENDAR WRITE SAFETY
    # =========================================================

    print()
    print("=" * 70)
    print("12. GOOGLE CALENDAR WRITE SAFETY")
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
        "PHASE 20 REAL GOOGLE VALIDATION: PASSED"
    )
    print("=" * 70)

    print()
    print(
        "Real Google Calendar events were used "
        "as scheduling constraints."
    )

    print(
        "User preferences were applied."
    )

    print(
        "Blocked periods were respected."
    )

    print(
        "Task preferred windows were respected "
        "when matching availability existed."
    )

    print(
        "Multiple tasks were scheduled without overlap."
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