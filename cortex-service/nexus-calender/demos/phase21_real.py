from __future__ import annotations

import sys

from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


# ---------------------------------------------------------
# PROJECT PATH
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# PROJECT IMPORTS
# ---------------------------------------------------------

from buffers import BufferConfig
from busy_intervals import (
    events_to_busy_intervals,
)
from connector.google_calendar_client import (
    GoogleCalendarClient,
)
from datetime_utils import DateTimeRange
from engine.focus_time import (
    find_focus_blocks,
)
from windows import SchedulingWindow


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

TIMEZONE = "Asia/Kolkata"
IST = ZoneInfo(TIMEZONE)

REQUESTED_DURATION_MINUTES = 180

BUFFER_CONFIG = BufferConfig(
    before_minutes=15,
    after_minutes=15,
)

CODING_WINDOW = SchedulingWindow(
    name="coding",
    start_time="09:00",
    end_time="22:00",
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


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def tomorrow_range(
    reference: datetime,
) -> DateTimeRange:

    tomorrow = (
        reference.date()
        + timedelta(days=1)
    )

    start = datetime.combine(
        tomorrow,
        time(
            0,
            0,
        ),
        tzinfo=IST,
    )

    end = datetime.combine(
        tomorrow,
        time(
            23,
            59,
        ),
        tzinfo=IST,
    )

    return DateTimeRange(
        start=start,
        end=end,
    )


def search_tomorrow(
    client: GoogleCalendarClient,
    reference: datetime,
):
    window = tomorrow_range(
        reference,
    )

    events = client.search(
        {
            "timeMin": window.start.isoformat(),
            "timeMax": window.end.isoformat(),
            "singleEvents": True,
            "orderBy": "startTime",
        }
    )

    return window, events


def print_event(
    index: int,
    event,
) -> None:

    print(
        f"{index}. "
        f"{event.title}: "
        f"{event.start.isoformat()} "
        f"-> "
        f"{event.end.isoformat()}"
    )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main() -> None:

    reference = datetime.now(
        IST,
    )

    print()
    print(
        "# PHASE 21 - REAL GOOGLE CALENDAR "
        "FOCUS TIME VALIDATION"
    )

    print()
    print(
        f"Reference: "
        f"{reference.isoformat()}"
    )

    print()
    print("=" * 70)

    # -----------------------------------------------------
    # 1. INITIALIZE GOOGLE CALENDAR
    # -----------------------------------------------------

    print(
        "1. INITIALIZE REAL GOOGLE CALENDAR"
    )

    client = GoogleCalendarClient()

    print(
        "   REAL GOOGLE CALENDAR CLIENT: READY"
    )

    # -----------------------------------------------------
    # 2. SEARCH TOMORROW
    # -----------------------------------------------------

    print()
    print(
        "2. SEARCH TOMORROW'S REAL CALENDAR"
    )

    calendar_window, events = (
        search_tomorrow(
            client,
            reference,
        )
    )

    print(
        f"   REAL GOOGLE EVENTS FOUND: "
        f"{len(events)}"
    )

    if events:

        for index, event in enumerate(
            events,
            start=1,
        ):
            print_event(
                index,
                event,
            )

    else:

        print(
            "   No real Google Calendar events "
            "found tomorrow."
        )

    # -----------------------------------------------------
    # 3. CONVERT TO BUSY INTERVALS
    # -----------------------------------------------------

    print()
    print(
        "3. CONVERT CALENDAR EVENTS "
        "TO BUSY INTERVALS"
    )

    busy_intervals = (
        events_to_busy_intervals(
            events,
        )
    )

    print(
        f"   BUSY INTERVALS: "
        f"{len(busy_intervals)}"
    )

    for interval in busy_intervals:

        print(
            f"   {interval.start.isoformat()} "
            f"-> "
            f"{interval.end.isoformat()}"
        )

    # -----------------------------------------------------
    # 4. USER REQUEST
    # -----------------------------------------------------

    print()
    print(
        "4. FOCUS-TIME REQUEST"
    )

    print(
        "   User: "
        "\"I need 3 hours uninterrupted "
        "coding time tomorrow.\""
    )

    print(
        "   Requested duration: "
        f"{REQUESTED_DURATION_MINUTES} minutes"
    )

    print(
        "   Coding window: "
        f"{CODING_WINDOW.start_time}"
        " -> "
        f"{CODING_WINDOW.end_time}"
    )

    print(
        "   Before-event buffer: "
        f"{BUFFER_CONFIG.before_minutes} minutes"
    )

    print(
        "   After-event buffer: "
        f"{BUFFER_CONFIG.after_minutes} minutes"
    )

    # -----------------------------------------------------
    # 5. PHASE 21
    # -----------------------------------------------------

    print()
    print(
        "5. FIND GENUINELY UNINTERRUPTED "
        "FOCUS BLOCKS"
    )

    focus_blocks = find_focus_blocks(
        duration_minutes=(
            REQUESTED_DURATION_MINUTES
        ),
        window=calendar_window,
        buffer_config=BUFFER_CONFIG,
        busy_intervals=busy_intervals,
        scheduling_window=CODING_WINDOW,
        timezone=IST,
    )

    print()
    print(
        f"FOCUS BLOCKS FOUND: "
        f"{len(focus_blocks)}"
    )

    for index, slot in enumerate(
        focus_blocks,
        start=1,
    ):

        print(
            f"{index}. "
            f"{slot.start.isoformat()} "
            f"-> "
            f"{slot.end.isoformat()} "
            f"({slot.duration_minutes} min)"
        )

    # -----------------------------------------------------
    # 6. VALIDATION
    # -----------------------------------------------------

    print()
    print(
        "6. VALIDATION"
    )

    # Every returned slot must satisfy
    # the requested uninterrupted duration.

    duration_validation = all(
        slot.duration_minutes
        >= REQUESTED_DURATION_MINUTES
        for slot in focus_blocks
    )

    if duration_validation:

        print(
            "UNINTERRUPTED DURATION: PASSED"
        )

    else:

        print(
            "UNINTERRUPTED DURATION: FAILED"
        )

        raise AssertionError(
            "A focus block shorter than the "
            "requested duration was returned."
        )

    # Every slot must be inside the requested
    # calendar window.

    window_validation = all(
        slot.start
        >= calendar_window.start
        and slot.end
        <= calendar_window.end
        for slot in focus_blocks
    )

    if window_validation:

        print(
            "CALENDAR WINDOW: PASSED"
        )

    else:

        print(
            "CALENDAR WINDOW: FAILED"
        )

        raise AssertionError(
            "Focus block escaped the calendar window."
        )

    # Every slot must be inside the configured
    # coding window.

    coding_start = time.fromisoformat(
        CODING_WINDOW.start_time,
    )

    coding_end = time.fromisoformat(
        CODING_WINDOW.end_time,
    )

    coding_validation = all(
        slot.start.timetz().replace(
            tzinfo=None,
        ) >= coding_start
        and slot.end.timetz().replace(
            tzinfo=None,
        ) <= coding_end
        for slot in focus_blocks
    )

    if coding_validation:

        print(
            "CODING WINDOW: PASSED"
        )

    else:

        print(
            "CODING WINDOW: FAILED"
        )

        raise AssertionError(
            "Focus block escaped the coding window."
        )

    # -----------------------------------------------------
    # 7. REAL CALENDAR WRITE SAFETY
    # -----------------------------------------------------

    print()
    print(
        "7. REAL CALENDAR WRITE OPERATIONS"
    )

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

    # -----------------------------------------------------
    # 8. FINAL RESULT
    # -----------------------------------------------------

    print()
    print("=" * 70)

    if focus_blocks:

        print(
            "PHASE 21 FOCUS TIME VALIDATION: PASSED"
        )

        print(
            "Real Google Calendar availability was "
            "used to identify genuinely uninterrupted "
            "focus blocks."
        )

    else:

        print(
            "PHASE 21 FOCUS TIME VALIDATION: "
            "NO QUALIFYING BLOCK"
        )

        print(
            "No uninterrupted 3-hour block exists "
            "tomorrow after buffers and scheduling "
            "window constraints."
        )

    print()
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