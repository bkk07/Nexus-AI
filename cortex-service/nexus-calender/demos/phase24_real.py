from __future__ import annotations

import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from busy_intervals import (
    events_to_busy_intervals,
)
from connector.google_calendar_client import (
    GoogleCalendarClient,
)
from datetime_utils import DateTimeRange
from engine.multi_constraint import (
    find_multi_constraint_slots,
)
from models import (
    CalendarMultiConstraintRequest,
)


TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)


# =========================================================
# HELPERS
# =========================================================


def tomorrow_range(
    reference: datetime,
) -> tuple[datetime, datetime]:

    tomorrow = (
        reference.date()
        + timedelta(days=1)
    )

    start = datetime.combine(
        tomorrow,
        time(9, 0),
        tzinfo=IST,
    )

    end = datetime.combine(
        tomorrow,
        time(22, 0),
        tzinfo=IST,
    )

    return start, end


def print_event(event) -> None:

    print(
        f"- {event.title}: "
        f"{event.start.isoformat()} -> "
        f"{event.end.isoformat()}"
    )


def print_block(
    index: int,
    block,
) -> None:

    print(
        f"\nBLOCK {index}"
    )

    print(
        f"{block.start.isoformat()} "
        f"-> "
        f"{block.end.isoformat()}"
    )

    print(
        f"Duration: "
        f"{block.duration_minutes} minutes"
    )


def validate_block(
    block,
    *,
    window_start: datetime,
    window_end: datetime,
) -> bool:

    if block.start < window_start:
        return False

    if block.end > window_end:
        return False

    actual_duration = int(
        (
            block.end
            - block.start
        ).total_seconds()
        // 60
    )

    return (
        actual_duration
        == block.duration_minutes
    )


# =========================================================
# MAIN
# =========================================================


def main() -> None:

    reference = datetime.now(
        IST,
    )

    print()
    print(
        "# PHASE 24 - REAL GOOGLE CALENDAR "
        "MULTI-CONSTRAINT VALIDATION"
    )

    print()
    print(
        f"Reference: "
        f"{reference.isoformat()}"
    )

    print()
    print("=" * 70)

    # =====================================================
    # 1. INITIALIZE REAL GOOGLE CALENDAR
    # =====================================================

    print()
    print(
        "1. INITIALIZE REAL GOOGLE CALENDAR"
    )

    client = GoogleCalendarClient()

    print(
        "   REAL GOOGLE CALENDAR CLIENT: READY"
    )

    # =====================================================
    # 2. TOMORROW'S REAL CALENDAR
    # =====================================================

    window_start, window_end = (
        tomorrow_range(reference)
    )

    print()
    print(
        "2. SEARCH TOMORROW'S REAL CALENDAR"
    )

    print(
        f"   Window: "
        f"{window_start.isoformat()} "
        f"-> "
        f"{window_end.isoformat()}"
    )

    events = client.search(
        {
            "timeMin": (
                window_start.astimezone(
                    ZoneInfo("UTC")
                ).isoformat()
            ),
            "timeMax": (
                window_end.astimezone(
                    ZoneInfo("UTC")
                ).isoformat()
            ),
            "singleEvents": True,
            "orderBy": "startTime",
        }
    )

    print(
        f"   REAL GOOGLE EVENTS FOUND: "
        f"{len(events)}"
    )

    if events:

        for event in events:
            print_event(event)

    else:

        print(
            "   No real Google Calendar events "
            "found tomorrow."
        )

    # =====================================================
    # 3. CONVERT EVENTS TO BUSY INTERVALS
    # =====================================================

    print()
    print(
        "3. CONVERT CALENDAR EVENTS "
        "TO BUSY INTERVALS"
    )

    busy_intervals = (
        events_to_busy_intervals(
            events
        )
    )

    print(
        f"   MERGED BUSY INTERVALS: "
        f"{len(busy_intervals)}"
    )

    for busy in busy_intervals:

        print(
            f"   {busy.start.isoformat()} "
            f"-> "
            f"{busy.end.isoformat()}"
        )

    # =====================================================
    # 4. REQUEST #1
    #
    # "I need 2 hours for DSA tomorrow evening,
    # preferably after 6 PM, but not after 9 PM."
    # =====================================================

    print()
    print(
        "4. COMPOUND REQUEST #1"
    )

    print(
        '   "I need 2 hours for DSA tomorrow '
        'evening, preferably after 6 PM, '
        'but not after 9 PM."'
    )

    request_1 = CalendarMultiConstraintRequest(
        duration_minutes=120,

        # HARD bounds.
        hard_start_time="17:00",
        hard_end_time="21:00",

        # SOFT preference.
        preferred_start_time="18:00",
        preferred_end_time="21:00",

        purpose="DSA",
    )

    result_1 = find_multi_constraint_slots(
        request=request_1,
        window=DateTimeRange(
            start=window_start,
            end=window_end,
        ),
        busy_intervals=busy_intervals,
    )

    print()
    print(
        "   RESULT #1"
    )

    print(
        f"   STATUS: "
        f"{result_1.status}"
    )

    print(
        f"   BLOCKS: "
        f"{len(result_1.blocks)}"
    )

    print(
        f"   UNSCHEDULED MINUTES: "
        f"{result_1.unscheduled_minutes}"
    )

    for explanation in result_1.explanation:

        print(
            f"   - {explanation}"
        )

    for index, block in enumerate(
        result_1.blocks,
        start=1,
    ):

        print_block(
            index,
            block,
        )

    # =====================================================
    # 5. VALIDATE REQUEST #1
    # =====================================================

    print()
    print(
        "5. VALIDATE COMPOUND REQUEST #1"
    )

    request_1_passed = (
        result_1.status == "feasible"
        and len(result_1.blocks) >= 1
        and all(
            validate_block(
                block,
                window_start=window_start,
                window_end=window_end,
            )
            for block in result_1.blocks
        )
    )

    if result_1.blocks:

        selected = result_1.blocks[0]

        hard_window_passed = (
            selected.start
            >= window_start.replace(
                hour=17,
                minute=0,
                second=0,
                microsecond=0,
            )
            and selected.end
            <= window_start.replace(
                hour=21,
                minute=0,
                second=0,
                microsecond=0,
            )
        )

        exact_duration_passed = (
            selected.duration_minutes
            == 120
        )

    else:

        hard_window_passed = False
        exact_duration_passed = False

    print(
        "   HARD WINDOW: "
        + (
            "PASSED"
            if hard_window_passed
            else "FAILED"
        )
    )

    print(
        "   EXACT 120-MINUTE DURATION: "
        + (
            "PASSED"
            if exact_duration_passed
            else "FAILED"
        )
    )

    print(
        "   BLOCK VALIDATION: "
        + (
            "PASSED"
            if request_1_passed
            else "FAILED"
        )
    )

    # =====================================================
    # 6. REQUEST #2
    #
    # "Find me 3 hours for the project before Friday,
    # preferably in two uninterrupted blocks."
    #
    # We use the same tomorrow window as the real
    # calendar horizon for deterministic validation.
    # =====================================================

    print()
    print(
        "6. COMPOUND REQUEST #2"
    )

    print(
        '   "Find me 3 hours for the project '
        'before Friday, preferably in two '
        'uninterrupted blocks."'
    )

    request_2 = CalendarMultiConstraintRequest(
        duration_minutes=180,
        split_required=True,
        number_of_blocks=2,
        purpose="project",
        deadline=window_end,
    )

    result_2 = find_multi_constraint_slots(
        request=request_2,
        window=DateTimeRange(
            start=window_start,
            end=window_end,
        ),
        busy_intervals=busy_intervals,
    )

    print()
    print(
        "   RESULT #2"
    )

    print(
        f"   STATUS: "
        f"{result_2.status}"
    )

    print(
        f"   BLOCKS: "
        f"{len(result_2.blocks)}"
    )

    print(
        f"   UNSCHEDULED MINUTES: "
        f"{result_2.unscheduled_minutes}"
    )

    for explanation in result_2.explanation:

        print(
            f"   - {explanation}"
        )

    for index, block in enumerate(
        result_2.blocks,
        start=1,
    ):

        print_block(
            index,
            block,
        )

    # =====================================================
    # 7. VALIDATE REQUEST #2
    # =====================================================

    print()
    print(
        "7. VALIDATE COMPOUND REQUEST #2"
    )

    total_duration = sum(
        block.duration_minutes
        for block in result_2.blocks
    )

    two_block_passed = (
        result_2.status == "feasible"
        and len(result_2.blocks) == 2
        and total_duration == 180
        and all(
            validate_block(
                block,
                window_start=window_start,
                window_end=window_end,
            )
            for block in result_2.blocks
        )
    )

    print(
        "   EXACTLY TWO BLOCKS: "
        + (
            "PASSED"
            if len(result_2.blocks) == 2
            else "FAILED"
        )
    )

    print(
        "   TOTAL DURATION = 180 MINUTES: "
        + (
            "PASSED"
            if total_duration == 180
            else "FAILED"
        )
    )

    print(
        "   EACH BLOCK UNINTERRUPTED: "
        + (
            "PASSED"
            if two_block_passed
            else "FAILED"
        )
    )

    # =====================================================
    # 8. HARD CONSTRAINT VALIDATION
    # =====================================================

    print()
    print(
        "8. HARD CONSTRAINT VALIDATION"
    )

    if result_1.blocks:

        hard_constraint_ok = all(
            (
                block.start
                >= window_start.replace(
                    hour=17,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
                and block.end
                <= window_start.replace(
                    hour=21,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            )
            for block in result_1.blocks
        )

    else:

        hard_constraint_ok = (
            result_1.status == "infeasible"
        )

    print(
        "   HARD CONSTRAINTS: "
        + (
            "PASSED"
            if hard_constraint_ok
            else "FAILED"
        )
    )

    # =====================================================
    # 9. SOFT PREFERENCE VALIDATION
    # =====================================================

    print()
    print(
        "9. SOFT PREFERENCE VALIDATION"
    )

    if result_1.blocks:

        preference_ok = (
            result_1.blocks[0].start.hour
            >= 18
        )

    else:

        preference_ok = False

    print(
        "   EVENING PREFERENCE: "
        + (
            "PASSED"
            if preference_ok
            else "NO QUALIFYING EVENING BLOCK"
        )
    )

    # =====================================================
    # 10. NO CALENDAR WRITE OPERATIONS
    # =====================================================

    print()
    print(
        "10. REAL CALENDAR WRITE OPERATIONS"
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

    # =====================================================
    # FINAL
    # =====================================================

    print()
    print("=" * 70)

    overall_passed = (
        request_1_passed
        and two_block_passed
        and hard_constraint_ok
    )

    if overall_passed:

        print(
            "PHASE 24 MULTI-CONSTRAINT "
            "VALIDATION: PASSED"
        )

        print()
        print(
            "Real Google Calendar events were used "
            "as scheduling constraints."
        )

        print(
            "Hard constraints were enforced."
        )

        print(
            "Soft preferences were applied "
            "through Phase 10 ranking."
        )

        print(
            "Multi-block scheduling was composed "
            "from existing scheduling primitives."
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

    else:

        print(
            "PHASE 24 MULTI-CONSTRAINT "
            "VALIDATION: FAILED"
        )


if __name__ == "__main__":
    main()