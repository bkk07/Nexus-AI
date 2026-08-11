from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from typing import Any, Mapping
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "Asia/Kolkata"


# ============================================================
# Calendar Semantic Model
# ============================================================

class CalendarQueryConstraints:
    """Typed calendar semantic constraints (internal, not LLM-facing)."""

    def __init__(self, **kwargs):
        self.query = kwargs.get("query")
        self.summary = kwargs.get("summary")
        self.event_id = kwargs.get("event_id")
        self.start = kwargs.get("start")
        self.end = kwargs.get("end")
        self.time_range = kwargs.get("time_range")
        self.time_min = kwargs.get("time_min")
        self.time_max = kwargs.get("time_max")
        self.time_zone = kwargs.get("time_zone") or kwargs.get("timeZone") or DEFAULT_TIMEZONE
        self.location = kwargs.get("location")
        self.description = kwargs.get("description")
        self.top_k = kwargs.get("top_k")
        self.is_all_day = kwargs.get("is_all_day")

    def model_dump(self, exclude_none=True):
        d = {
            "query": self.query,
            "summary": self.summary,
            "event_id": self.event_id,
            "start": self.start,
            "end": self.end,
            "time_range": self.time_range,
            "time_min": self.time_min,
            "time_max": self.time_max,
            "time_zone": self.time_zone,
            "location": self.location,
            "description": self.description,
            "top_k": self.top_k,
            "is_all_day": self.is_all_day,
        }
        if exclude_none:
            return {k: v for k, v in d.items() if v is not None}
        return d


def compile_calendar_query(
    semantic_parameters: Mapping[str, Any] | CalendarQueryConstraints,
    today_override: date | None = None,
    now_override: datetime | None = None,
) -> dict[str, Any]:
    """
    Deterministic Calendar query compiler.

    Converts semantic constraints into Google Calendar API parameters:
        q, timeMin, timeMax, timeZone, singleEvents, orderBy
    """
    params = _normalize(semantic_parameters)
    today = today_override or date.today()
    tz_name = _clean_tz(params.get("time_zone") or params.get("timeZone") or DEFAULT_TIMEZONE)
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo(DEFAULT_TIMEZONE)
        tz_name = DEFAULT_TIMEZONE

    result: dict[str, Any] = {}
    result["timeZone"] = tz_name
    result["singleEvents"] = True
    result["orderBy"] = "startTime"

    # query mapping: summary or query -> q
    q = _clean_string(params.get("query"))
    summary = _clean_string(params.get("summary"))
    if not q and summary:
        q = summary
    if q:
        result["q"] = q

    # top_k
    top_k = params.get("top_k")
    if top_k is not None:
        try:
            result["maxResults"] = int(top_k)
        except Exception:
            pass

    # Explicit timeMin/timeMax if already ISO (direct)
    time_min_raw = params.get("time_min") or params.get("timeMin")
    time_max_raw = params.get("time_max") or params.get("timeMax")

    # If time_min/max already look like ISO with T, preserve
    if isinstance(time_min_raw, str) and "T" in time_min_raw:
        result["timeMin"] = time_min_raw
    if isinstance(time_max_raw, str) and "T" in time_max_raw:
        result["timeMax"] = time_max_raw

    # Determine time bounds from time_range and start/end
    start_raw = params.get("start")
    end_raw = params.get("end")
    time_range = _clean_string(params.get("time_range"))

    # If start/end provided and not already handled as timeMin/timeMax
    has_start_end = start_raw is not None or end_raw is not None

    # Compile time range bounds if needed
    if time_range and not has_start_end and "timeMin" not in result:
        # Only time_range without start/end -> use time_range bounds
        tmin, tmax = _compile_time_range_to_iso(time_range, today, tz)
        if tmin:
            result["timeMin"] = tmin
        if tmax:
            result["timeMax"] = tmax
    elif has_start_end:
        # Parse start/end, potentially merging with time_range date hint
        s_dt, e_dt = _parse_start_end(start_raw, end_raw, time_range, today, tz)
        if s_dt is not None:
            result["timeMin"] = s_dt.isoformat()
        elif "timeMin" not in result and time_range:
            # fallback to time_range's tmin if start parsing failed
            tmin, _ = _compile_time_range_to_iso(time_range, today, tz)
            if tmin:
                result["timeMin"] = tmin

        if e_dt is not None:
            result["timeMax"] = e_dt.isoformat()
        elif "timeMax" not in result and time_range:
            _, tmax = _compile_time_range_to_iso(time_range, today, tz)
            if tmax:
                result["timeMax"] = tmax

        # Validation: end must be after start
        if s_dt and e_dt and e_dt <= s_dt:
            # check if this was explicitly overnight case that should have been advanced
            # _parse_start_end should have already handled overnight.
            # If still invalid, raise
            raise ValueError(f"Invalid time range: end {e_dt} must be after start {s_dt}")

        # If we have midnight-to-midnight range due to date-only, ensure timeMax is exclusive (next day midnight)
    elif time_range and "timeMin" not in result:
        tmin, tmax = _compile_time_range_to_iso(time_range, today, tz)
        if tmin:
            result["timeMin"] = tmin
        if tmax:
            result["timeMax"] = tmax

    # Preserve extra fields for internal use (location, description, event_id, etc.) if needed for CREATE/UPDATE
    # But for query compiler, only return API-relevant keys
    # Keep query-related constraints for deterministic duplicate checks
    if params.get("description"):
        result["description"] = params["description"]
    if params.get("location"):
        result["location"] = params["location"]
    if params.get("event_id") or params.get("eventId"):
        result["eventId"] = params.get("event_id") or params.get("eventId")
    if summary:
        result["summary"] = summary
    if params.get("is_all_day") is not None:
        result["isAllDay"] = params["is_all_day"]

    # Clean up: remove None values
    return {k: v for k, v in result.items() if v is not None}


def _normalize(semantic_parameters) -> dict[str, Any]:
    if isinstance(semantic_parameters, CalendarQueryConstraints):
        return semantic_parameters.model_dump(exclude_none=True)
    if hasattr(semantic_parameters, "model_dump"):
        try:
            return semantic_parameters.model_dump(exclude_none=True)
        except Exception:
            pass
    if isinstance(semantic_parameters, Mapping):
        return {k: v for k, v in semantic_parameters.items() if v is not None}
    return dict(semantic_parameters)


def _clean_string(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return " ".join(text.split())


def _clean_tz(value: Any) -> str:
    if not value:
        return DEFAULT_TIMEZONE
    t = str(value).strip()
    return t or DEFAULT_TIMEZONE


def _compile_time_range_to_iso(time_range: str, today: date, tz: ZoneInfo) -> tuple[str | None, str | None]:
    """Convert time_range semantic to ISO timeMin/timeMax."""
    if not time_range:
        return None, None
    norm = time_range.strip().lower().replace(" ", "_")

    def midnight(d: date) -> datetime:
        return datetime.combine(d, time.min, tzinfo=tz)

    if norm == "today":
        tmin = midnight(today)
        tmax = midnight(today + timedelta(days=1))
        return tmin.isoformat(), tmax.isoformat()
    if norm == "tomorrow":
        tmin = midnight(today + timedelta(days=1))
        tmax = midnight(today + timedelta(days=2))
        return tmin.isoformat(), tmax.isoformat()
    if norm == "yesterday":
        tmin = midnight(today - timedelta(days=1))
        tmax = midnight(today)
        return tmin.isoformat(), tmax.isoformat()
    if norm in ("this_week", "thisweek"):
        start_of_week = today - timedelta(days=today.weekday())
        tmin = midnight(start_of_week)
        # End is start + 7 days
        tmax = midnight(start_of_week + timedelta(days=7))
        return tmin.isoformat(), tmax.isoformat()
    if norm in ("next_week", "nextweek"):
        start_of_this_week = today - timedelta(days=today.weekday())
        start_next = start_of_this_week + timedelta(days=7)
        tmin = midnight(start_next)
        tmax = midnight(start_next + timedelta(days=7))
        return tmin.isoformat(), tmax.isoformat()
    if norm in ("last_week", "lastweek"):
        start_of_this_week = today - timedelta(days=today.weekday())
        start_last = start_of_this_week - timedelta(days=7)
        tmin = midnight(start_last)
        tmax = midnight(start_of_this_week)
        return tmin.isoformat(), tmax.isoformat()
    if norm in ("this_month", "thismonth"):
        start = today.replace(day=1)
        # next month first day
        if start.month == 12:
            nxt = start.replace(year=start.year + 1, month=1)
        else:
            nxt = start.replace(month=start.month + 1)
        return midnight(start).isoformat(), midnight(nxt).isoformat()
    if norm in ("last_month", "lastmonth"):
        start_this = today.replace(day=1)
        last_day = start_this - timedelta(days=1)
        start_last = last_day.replace(day=1)
        return midnight(start_last).isoformat(), midnight(start_this).isoformat()
    if norm in ("next_month", "nextmonth"):
        if today.month == 12:
            start_next = date(today.year + 1, 1, 1)
            if start_next.month == 12:
                end_next = date(start_next.year + 1, 1, 1)
            else:
                end_next = date(start_next.year, start_next.month + 1, 1)
        else:
            start_next = date(today.year, today.month + 1, 1)
            if start_next.month == 12:
                end_next = date(start_next.year + 1, 1, 1)
            else:
                end_next = date(start_next.year, start_next.month + 1, 1)
        return midnight(start_next).isoformat(), midnight(end_next).isoformat()
    # Handle weekdays like "next_monday", "monday"
    weekdays = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
    for name, idx in weekdays.items():
        if norm == name or norm == f"next_{name}" or norm == f"this_{name}":
            # Find next occurrence of that weekday
            days_ahead = (idx - today.weekday()) % 7
            if norm.startswith("next_") and days_ahead == 0:
                days_ahead = 7
            # If today is Monday and norm is "monday" and we interpret as today, days_ahead 0 -> today
            # For this_week monday, if today is monday, it's today
            target = today + timedelta(days=days_ahead)
            # If "next_monday" and today is monday, we want next monday (7 days ahead) – already handled
            # If just "monday" and target is in past? But we treat as next occurrence
            tmin = midnight(target)
            tmax = midnight(target + timedelta(days=1))
            return tmin.isoformat(), tmax.isoformat()
    # Handle "tonight", "this_afternoon", etc.
    if norm in ("tonight", "this_afternoon", "this_evening", "afternoon", "evening", "morning"):
        # Map to today's range but narrow to evening/afternoon? For search, use today's full day.
        # Could refine: morning 5-12, afternoon 12-17, evening 17-22, tonight 18-23
        # But for deterministic, return today range to avoid missing events.
        tmin = midnight(today)
        tmax = midnight(today + timedelta(days=1))
        return tmin.isoformat(), tmax.isoformat()
    return None, None


def _parse_start_end(
    start_raw: Any,
    end_raw: Any,
    time_range: str | None,
    today: date,
    tz: ZoneInfo,
) -> tuple[datetime | None, datetime | None]:
    """Parse start/end semantic strings into datetimes."""
    start_dt = None
    end_dt = None
    # Determine base date hint from time_range if available
    time_range_date = None
    if time_range:
        norm = time_range.strip().lower().replace(" ", "_")
        if norm == "today":
            time_range_date = today
        elif norm == "tomorrow":
            time_range_date = today + timedelta(days=1)
        elif norm == "yesterday":
            time_range_date = today - timedelta(days=1)
        else:
            # Try to parse weekday from time_range
            weekdays = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
            for name, idx in weekdays.items():
                if name in norm:
                    days_ahead = (idx - today.weekday()) % 7
                    if "next" in norm and days_ahead == 0:
                        days_ahead = 7
                    time_range_date = today + timedelta(days=days_ahead)
                    break

    if start_raw is not None:
        s = str(start_raw).strip()
        # If s is already ISO with T, parse directly
        if "T" in s and "-" in s:
            try:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz)
                start_dt = dt.astimezone(tz)
            except Exception:
                start_dt = _parse_natural_datetime(s, today, tz, time_range_date)
        else:
            start_dt = _parse_natural_datetime(s, today, tz, time_range_date)

    if end_raw is not None:
        e = str(end_raw).strip()
        if "T" in e and "-" in e:
            try:
                dt = datetime.fromisoformat(e.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz)
                end_dt = dt.astimezone(tz)
            except Exception:
                end_dt = _parse_natural_datetime(e, today, tz, time_range_date)
        else:
            end_dt = _parse_natural_datetime(e, today, tz, time_range_date)

    # Overnight handling: if end <= start, assume next day
    if start_dt and end_dt and end_dt <= start_dt:
        # Check if original strings indicated overnight (e.g., 12 PM to 1 AM)
        # Heuristic: if end hour < start hour or end is AM when start is PM, advance by one day
        # For determinism, always advance end by one day if end <= start and both have time components
        # But do not advance if user explicitly supplied separate dates (detected by containing date qualifier in both)
        start_has_date = _contains_date_hint(str(start_raw)) if start_raw else False
        end_has_date = _contains_date_hint(str(end_raw)) if end_raw else False
        if not (start_has_date and end_has_date):
            # If end was parsed to same date as start and end <= start, advance
            # Check if time_range hint indicates same date; then overnight is intentional
            end_dt = end_dt + timedelta(days=1)
        # else if both have explicit dates, leave as is and let validation fail later if still <=

    return start_dt, end_dt


def _contains_date_hint(s: str) -> bool:
    lower = s.lower()
    for kw in ["today", "tomorrow", "yesterday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "next", "this"]:
        if kw in lower:
            return True
    # Check ISO date pattern
    if re.search(r"\d{4}-\d{2}-\d{2}", s):
        return True
    # Check date like 2026/08/10
    if re.search(r"\d{4}/\d{2}/\d{2}", s):
        return True
    return False


def _parse_natural_datetime(value: str, today: date, tz: ZoneInfo, base_date_hint: date | None = None) -> datetime | None:
    if not value:
        return None
    v = value.strip().lower()
    # Remove extra spaces
    v = " ".join(v.split())

    # Determine base date from value itself
    base_date = base_date_hint or today
    # Check for explicit date qualifiers inside value
    if "tomorrow" in v:
        base_date = today + timedelta(days=1)
        v = v.replace("tomorrow", "").strip()
    elif "yesterday" in v:
        base_date = today - timedelta(days=1)
        v = v.replace("yesterday", "").strip()
    elif "today" in v:
        base_date = today
        v = v.replace("today", "").strip()
    else:
        weekdays = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
        for name, idx in weekdays.items():
            if name in v:
                days_ahead = (idx - today.weekday()) % 7
                if "next" in v and days_ahead == 0:
                    days_ahead = 7
                # Remove weekday tokens
                # Keep v for time parsing after removing date parts
                base_date = today + timedelta(days=days_ahead)
                # remove weekday and next/this qualifiers
                v = v.replace("next", "").replace("this", "").replace(name, "").strip()
                # Also remove leftover weekday modifiers like "morning", "afternoon" keep for now but they are not needed
                break

    # Handle qualifiers like "morning", "afternoon", "evening", "night" – keep but they don't affect time parsing directly
    for q in ["morning", "afternoon", "evening", "night", "tonight"]:
        if q in v:
            v = v.replace(q, "").strip()
    v = " ".join(v.split())

    if not v or v in ("",):
        # No time specified, default to midnight
        return datetime.combine(base_date, time.min, tzinfo=tz)

    # Try to parse time from v
    # Patterns: "7", "7 am", "7:00", "7:00 am", "19:00", "12 pm", "12 am"
    time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", v)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        ampm = time_match.group(3)

        if ampm:
            ampm = ampm.lower()
            if ampm == "am":
                if hour == 12:
                    hour = 0
            elif ampm == "pm":
                if hour != 12:
                    hour += 12
        else:
            # No am/pm, assume 24h if hour > 12? But if hour <=12 and no ampm, we need heuristic
            # If value was "7" without ampm, treat as 7:00 (assume AM? But spec example "7 to 9" for morning -> 7 AM to 9 AM)
            # We will keep as given; if hour <12 and no ampm, we treat as hour (24h). For afternoon/evening contexts, caller should have ampm.
            # We'll leave as is (hour as 24h)
            pass

        # Validate
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return datetime.combine(base_date, time(hour, minute), tzinfo=tz)

    # If ISO date string like "2026-08-10"
    iso_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", value)
    if iso_match:
        try:
            y, m, d = map(int, iso_match.groups())
            return datetime(y, m, d, tzinfo=tz)
        except Exception:
            pass

    # Fallback: try fromisoformat
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return dt.astimezone(tz)
    except Exception:
        pass

    return datetime.combine(base_date, time.min, tzinfo=tz)

