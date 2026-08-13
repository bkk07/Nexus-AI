from datetime import date, datetime
from zoneinfo import ZoneInfo

from models import TimeSlot
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


def slot(
    day: int,
    start_hour: int,
    end_hour: int,
) -> TimeSlot:

    start = dt(
        day,
        start_hour,
    )

    end = dt(
        day,
        end_hour,
    )

    duration = int(
        (end - start).total_seconds()
        // 60
    )

    return TimeSlot(
        start=start,
        end=end,
        duration_minutes=duration,
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


# =========================================================
# 1. SINGLE TASK
# =========================================================

def test_single_task_with_sufficient_capacity_is_fully_scheduled():

    task = Task(
        title="DSA",
        duration_minutes=120,
        deadline=date(
            2026,
            8,
            14,
        ),
    )

    available_slots = [
        slot(
            12,
            9,
            11,
        ),
        slot(
            12,
            14,
            17,
        ),
    ]

    result = schedule_task(
        task,
        available_slots,
    )

    assert result.status == "fully_scheduled"
    assert result.unscheduled_minutes == 0
    assert len(result.blocks) == 1

    assert (
        result.blocks[0].task_title
        == "DSA"
    )

    # Earliest suitable slot.
    assert (
        result.blocks[0].slot.start
        == dt(12, 9)
    )

    assert (
        result.blocks[0].slot.end
        == dt(12, 11)
    )

    assert (
        result.blocks[0].slot.duration_minutes
        == 120
    )


# =========================================================
# 2. DEADLINE UNREACHABLE
# =========================================================

def test_deadline_unreachable_reports_unscheduled_minutes():

    task = Task(
        title="Project",
        duration_minutes=180,
        deadline=date(
            2026,
            8,
            12,
        ),
    )

    available_slots = [
        slot(
            12,
            9,
            10,
        ),
        slot(
            12,
            11,
            12,
        ),
    ]

    result = schedule_task(
        task,
        available_slots,
    )

    assert (
        result.status
        == "insufficient_capacity"
    )

    assert (
        result.unscheduled_minutes
        == 180
    )

    assert result.blocks == []


# =========================================================
# 3. PRIORITY ORDERING
# =========================================================

def test_high_priority_task_is_scheduled_first():

    high_priority = Task(
        title="Important DSA",
        duration_minutes=120,
        priority="high",
    )

    low_priority = Task(
        title="Optional Reading",
        duration_minutes=120,
        priority="low",
    )

    available_slots = [
        slot(
            12,
            10,
            12,
        ),
    ]

    results = schedule_tasks(
        [
            low_priority,
            high_priority,
        ],
        available_slots,
    )

    assert (
        results["Important DSA"].status
        == "fully_scheduled"
    )

    assert (
        results["Important DSA"]
        .unscheduled_minutes
        == 0
    )

    assert (
        results["Optional Reading"].status
        == "insufficient_capacity"
    )

    assert (
        results["Optional Reading"]
        .unscheduled_minutes
        == 120
    )


# =========================================================
# 4. MULTIPLE TASKS
# NO DOUBLE BOOKING
# =========================================================

def test_multiple_tasks_never_share_the_same_slot():

    task_one = Task(
        title="Task A",
        duration_minutes=60,
        priority="high",
    )

    task_two = Task(
        title="Task B",
        duration_minutes=60,
        priority="medium",
    )

    available_slots = [
        slot(
            12,
            10,
            12,
        ),
    ]

    results = schedule_tasks(
        [
            task_one,
            task_two,
        ],
        available_slots,
    )

    first = results["Task A"]
    second = results["Task B"]

    assert (
        first.status
        == "fully_scheduled"
    )

    assert (
        second.status
        == "fully_scheduled"
    )

    assert len(first.blocks) == 1
    assert len(second.blocks) == 1

    first_slot = first.blocks[0].slot
    second_slot = second.blocks[0].slot

    # They must not overlap.
    assert (
        first_slot.end <= second_slot.start
        or second_slot.end <= first_slot.start
    )

    total_minutes = (
        first_slot.duration_minutes
        + second_slot.duration_minutes
    )

    assert total_minutes == 120


# =========================================================
# 5. SPLITTABLE TASK
# =========================================================

def test_splittable_task_is_divided_across_multiple_slots():

    task = Task(
        title="Coding",
        duration_minutes=180,
        splittable=True,
    )

    available_slots = [
        slot(
            12,
            9,
            10,
        ),
        slot(
            12,
            11,
            12,
        ),
        slot(
            12,
            15,
            16,
        ),
    ]

    result = schedule_task(
        task,
        available_slots,
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

    assert (
        result.blocks[0].slot.start
        == dt(12, 9)
    )

    assert (
        result.blocks[0].slot.end
        == dt(12, 10)
    )

    assert (
        result.blocks[1].slot.start
        == dt(12, 11)
    )

    assert (
        result.blocks[1].slot.end
        == dt(12, 12)
    )

    assert (
        result.blocks[2].slot.start
        == dt(12, 15)
    )

    assert (
        result.blocks[2].slot.end
        == dt(12, 16)
    )

    total_minutes = sum(
        block.slot.duration_minutes
        for block in result.blocks
    )

    assert total_minutes == 180


# =========================================================
# 6. NON-SPLITTABLE TASK
# =========================================================

def test_non_splittable_task_requires_one_complete_slot():

    task = Task(
        title="Deep Work",
        duration_minutes=120,
        splittable=False,
    )

    available_slots = [
        slot(
            12,
            9,
            10,
        ),
        slot(
            12,
            11,
            12,
        ),
    ]

    result = schedule_task(
        task,
        available_slots,
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
# 7. DEADLINE FILTERING
# =========================================================

def test_slots_after_deadline_are_not_used():

    task = Task(
        title="Revision",
        duration_minutes=60,
        deadline=date(
            2026,
            8,
            12,
        ),
    )

    available_slots = [
        slot(
            12,
            16,
            18,
        ),
        slot(
            13,
            9,
            10,
        ),
    ]

    result = schedule_task(
        task,
        available_slots,
    )

    assert (
        result.status
        == "fully_scheduled"
    )

    assert len(result.blocks) == 1

    assert (
        result.blocks[0].slot.start
        == dt(12, 16)
    )


# =========================================================
# 8. PREFERRED WINDOW
# =========================================================

def test_preferred_window_is_prioritized():

    task = Task(
        title="Study",
        duration_minutes=60,
        preferred_window=make_window(
            "study",
            "18:00",
            "22:00",
        ),
    )

    available_slots = [
        slot(
            12,
            10,
            11,
        ),
        slot(
            12,
            19,
            20,
        ),
    ]

    result = schedule_task(
        task,
        available_slots,
    )

    assert (
        result.status
        == "fully_scheduled"
    )

    assert len(result.blocks) == 1

    assert (
        result.blocks[0].slot.start
        == dt(12, 19)
    )

    assert (
        result.blocks[0].slot.end
        == dt(12, 20)
    )


# =========================================================
# 9. SPLITTABLE PARTIAL CAPACITY
# =========================================================

def test_splittable_task_reports_partial_capacity():

    task = Task(
        title="Large Project",
        duration_minutes=180,
        splittable=True,
    )

    available_slots = [
        slot(
            12,
            9,
            10,
        ),
        slot(
            12,
            11,
            12,
        ),
    ]

    result = schedule_task(
        task,
        available_slots,
    )

    assert (
        result.status
        == "partially_scheduled"
    )

    assert (
        result.unscheduled_minutes
        == 60
    )

    assert len(result.blocks) == 2

    scheduled_minutes = sum(
        block.slot.duration_minutes
        for block in result.blocks
    )

    assert scheduled_minutes == 120