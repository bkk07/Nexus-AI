from datetime import date, datetime
from zoneinfo import ZoneInfo

from busy_intervals import (
    BusyInterval,
    merge_busy_intervals,
)
from free_slots import find_free_slots
from models import EventSummary, TimeSlot
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


IST = ZoneInfo("Asia/Kolkata")


def dt(
    day: int,
    hour: int,
    minute: int = 0,
) -> datetime:
    return datetime(
        2026,
        8,
        day,
        hour,
        minute,
        tzinfo=IST,
    )


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


def make_event(
    event_id: str,
    start_hour: int,
    end_hour: int,
) -> EventSummary:
    return EventSummary(
        event_id=event_id,
        title=event_id,
        start=dt(
            12,
            start_hour,
        ),
        end=dt(
            12,
            end_hour,
        ),
    )


def make_busy(
    event_id: str,
    start_hour: int,
    end_hour: int,
) -> BusyInterval:
    return BusyInterval(
        start=dt(
            12,
            start_hour,
        ),
        end=dt(
            12,
            end_hour,
        ),
        source_event_ids=[
            event_id,
        ],
    )


# =========================================================
# 1. AVAILABILITY -> FREE SLOTS -> TASK
# =========================================================

def test_calendar_availability_to_task_scheduling():

    events = [
        make_event(
            "meeting-1",
            9,
            10,
        ),
        make_event(
            "meeting-2",
            13,
            14,
        ),
        make_event(
            "meeting-3",
            17,
            18,
        ),
    ]

    busy_intervals = [
        BusyInterval(
            start=event.start,
            end=event.end,
            source_event_ids=[
                event.event_id,
            ],
        )
        for event in events
    ]

    merged = merge_busy_intervals(
        busy_intervals,
    )

    window = make_datetime_range(
        9,
        18,
    )

    free_slots = find_free_slots(
        window=window,
        busy_intervals=merged,
        minimum_duration_minutes=60,
    )

    task = Task(
        title="DSA Practice",
        duration_minutes=120,
        deadline=date(
            2026,
            8,
            12,
        ),
    )

    result = schedule_task(
        task,
        free_slots,
    )

    assert (
        result.status
        == "fully_scheduled"
    )

    assert (
        result.unscheduled_minutes
        == 0
    )

    assert len(result.blocks) == 1

    # First suitable 120-minute free block:
    # 10:00 -> 13:00
    assert (
        result.blocks[0].slot.start
        == dt(12, 10)
    )

    assert (
        result.blocks[0].slot.end
        == dt(12, 12)
    )


# =========================================================
# 2. PREFERENCES + BLOCKED PERIOD
# =========================================================

def test_preferences_and_blocked_period_restrict_task_slots():

    preferences = UserPreferences(
        working_hours=make_window(
            "working_hours",
            "09:00",
            "18:00",
        ),
        blocked_periods=[
            make_window(
                "lunch",
                "13:00",
                "14:00",
            ),
        ],
        preferred_study_window=make_window(
            "study",
            "16:00",
            "18:00",
        ),
        minimum_focus_minutes=60,
    )

    blocked = blocked_windows_to_busy_intervals(
        date(
            2026,
            8,
            12,
        ),
        preferences,
        timezone=IST,
    )

    calendar_busy = [
        make_busy(
            "meeting-1",
            10,
            11,
        ),
    ]

    merged = merge_busy_intervals(
        calendar_busy + blocked,
    )

    window = make_datetime_range(
        9,
        18,
    )

    free_slots = find_free_slots(
        window=window,
        busy_intervals=merged,
        minimum_duration_minutes=60,
    )

    task = Task(
        title="Evening Study",
        duration_minutes=60,
        preferred_window=(
            preferences.preferred_study_window
        ),
    )

    result = schedule_task(
        task,
        free_slots,
    )

    assert (
        result.status
        == "fully_scheduled"
    )

    assert len(result.blocks) == 1

    selected = result.blocks[0].slot

    # Preferred study window should win.
    assert selected.start == dt(
        12,
        16,
    )

    assert selected.end == dt(
        12,
        17,
    )

    # Must not overlap lunch.
    assert not (
        selected.start < dt(12, 14)
        and selected.end > dt(12, 13)
    )


# =========================================================
# 3. MULTIPLE TASKS + PRIORITY + NO DOUBLE BOOKING
# =========================================================

def test_multiple_tasks_use_available_capacity_without_overlap():

    preferences = UserPreferences(
        working_hours=make_window(
            "working_hours",
            "09:00",
            "18:00",
        ),
        minimum_focus_minutes=60,
    )

    calendar_busy = [
        make_busy(
            "meeting-1",
            12,
            13,
        ),
    ]

    window = make_datetime_range(
        9,
        18,
    )

    free_slots = find_free_slots(
        window=window,
        busy_intervals=merge_busy_intervals(
            calendar_busy,
        ),
        minimum_duration_minutes=60,
    )

    high_priority = Task(
        title="Important DSA",
        duration_minutes=120,
        priority="high",
    )

    medium_priority = Task(
        title="System Design",
        duration_minutes=120,
        priority="medium",
    )

    results = schedule_tasks(
        [
            medium_priority,
            high_priority,
        ],
        free_slots,
    )

    high = results[
        "Important DSA"
    ]

    medium = results[
        "System Design"
    ]

    assert (
        high.status
        == "fully_scheduled"
    )

    assert (
        high.unscheduled_minutes
        == 0
    )

    assert (
        medium.status
        == "fully_scheduled"
    )

    assert (
        medium.unscheduled_minutes
        == 0
    )

    assert len(high.blocks) == 1
    assert len(medium.blocks) == 1

    high_slot = high.blocks[0].slot
    medium_slot = medium.blocks[0].slot

    # No double booking.
    assert (
        high_slot.end
        <= medium_slot.start
        or medium_slot.end
        <= high_slot.start
    )


# =========================================================
# 4. SPLITTABLE TASK ACROSS REAL FREE SLOTS
# =========================================================

def test_splittable_task_uses_multiple_free_slots():

    calendar_busy = [
        make_busy(
            "meeting-1",
            10,
            11,
        ),
        make_busy(
            "meeting-2",
            13,
            14,
        ),
        make_busy(
            "meeting-3",
            16,
            17,
        ),
    ]

    window = make_datetime_range(
        9,
        18,
    )

    free_slots = find_free_slots(
        window=window,
        busy_intervals=merge_busy_intervals(
            calendar_busy,
        ),
        minimum_duration_minutes=30,
    )

    task = Task(
        title="Large Project",
        duration_minutes=240,
        splittable=True,
    )

    result = schedule_task(
        task,
        free_slots,
    )

    assert (
        result.status
        == "fully_scheduled"
    )

    assert (
        result.unscheduled_minutes
        == 0
    )

    assert len(result.blocks) == 3

    total_minutes = sum(
        block.slot.duration_minutes
        for block in result.blocks
    )

    assert total_minutes == 240

    # 09:00 -> 10:00
    assert (
        result.blocks[0].slot.start
        == dt(12, 9)
    )

    assert (
        result.blocks[0].slot.end
        == dt(12, 10)
    )

    # 11:00 -> 13:00
    assert (
        result.blocks[1].slot.start
        == dt(12, 11)
    )

    assert (
        result.blocks[1].slot.end
        == dt(12, 13)
    )

    # 14:00 -> 16:00
    assert (
        result.blocks[2].slot.start
        == dt(12, 14)
    )

    assert (
        result.blocks[2].slot.end
        == dt(12, 15)
    )


# =========================================================
# 5. INSUFFICIENT CAPACITY
# =========================================================

def test_task_reports_insufficient_capacity_after_calendar_constraints():

    calendar_busy = [
        make_busy(
            "meeting-1",
            9,
            11,
        ),
        make_busy(
            "meeting-2",
            12,
            14,
        ),
        make_busy(
            "meeting-3",
            15,
            17,
        ),
    ]

    window = make_datetime_range(
        9,
        18,
    )

    free_slots = find_free_slots(
        window=window,
        busy_intervals=merge_busy_intervals(
            calendar_busy,
        ),
        minimum_duration_minutes=30,
    )

    task = Task(
        title="Deep Work",
        duration_minutes=120,
        splittable=False,
    )

    result = schedule_task(
        task,
        free_slots,
    )

    assert (
        result.status
        == "insufficient_capacity"
    )

    assert (
        result.unscheduled_minutes
        == 120
    )

    assert result.blocks == []


# =========================================================
# HELPER
# =========================================================

def make_datetime_range(
    start_hour: int,
    end_hour: int,
):
    from datetime_utils import DateTimeRange

    return DateTimeRange(
        start=dt(
            12,
            start_hour,
        ),
        end=dt(
            12,
            end_hour,
        ),
    )