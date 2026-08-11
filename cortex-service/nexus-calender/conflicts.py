from __future__ import annotations

from models import EventSummary
from datetime_utils import DateTimeRange


def find_conflicts(
    proposed_range: DateTimeRange,
    events: list[EventSummary],
) -> list[EventSummary]:
    """
    Return every individual calendar event that conflicts
    with the proposed time range.

    Conflict rule:

        event.start < proposed.end
        AND
        event.end > proposed.start

    Boundary-touching events are NOT conflicts.
    """

    conflicts: list[EventSummary] = []

    for event in events:

        if (
            event.start < proposed_range.end
            and event.end > proposed_range.start
        ):
            conflicts.append(event)

    return conflicts