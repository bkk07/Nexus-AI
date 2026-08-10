from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Mapping

from app.core.operation_planner import GmailQueryConstraints


def compile_gmail_query(
    semantic_parameters: Mapping[str, Any] | GmailQueryConstraints,
    today_override: date | None = None,
) -> str:
    parameters = _normalize_semantic_parameters(semantic_parameters)

    parts: list[str] = []

    sender = _clean_string(parameters.get("sender"))
    if sender:
        parts.append(f"from:({sender})")
        
    recipient = _clean_string(parameters.get("recipient"))
    if recipient:
        parts.append(f"to:({recipient})")

    cc = _clean_string(parameters.get("cc"))
    if cc:
        parts.append(f"cc:({cc})")

    bcc = _clean_string(parameters.get("bcc"))
    if bcc:
        parts.append(f"bcc:({bcc})")

    if parameters.get("unread") is True:
        parts.append("is:unread")
        
    if parameters.get("read") is True:
        parts.append("is:read")

    if parameters.get("starred") is True:
        parts.append("is:starred")
        
    if parameters.get("important") is True:
        parts.append("is:important")

    if parameters.get("inbox") is True:
        parts.append("in:inbox")
        
    if parameters.get("sent") is True:
        parts.append("in:sent")

    if parameters.get("trash") is True:
        parts.append("in:trash")

    if parameters.get("spam") is True:
        parts.append("in:spam")

    if parameters.get("has_attachment") is True:
        parts.append("has:attachment")

    attachment_type = _clean_string(parameters.get("attachment_type"))
    if attachment_type:
        parts.append(f"filename:({attachment_type})")

    subject = _clean_string(parameters.get("subject"))
    if subject:
        parts.append(f"subject:({subject})")

    keyword = _clean_string(parameters.get("keyword"))
    if keyword:
        parts.append(keyword)

    time_range = _clean_string(parameters.get("time_range"))
    today = today_override or date.today()
    if time_range:
        parts.extend(_compile_time_range(time_range, today))
        
    after_date = _clean_string(parameters.get("after_date"))
    if after_date:
        parts.append(f"after:{after_date}")

    before_date = _clean_string(parameters.get("before_date"))
    if before_date:
        parts.append(f"before:{before_date}")

    return " ".join(parts)


def _normalize_semantic_parameters(
    semantic_parameters: Mapping[str, Any] | GmailQueryConstraints,
) -> dict[str, Any]:
    if isinstance(semantic_parameters, GmailQueryConstraints):
        return semantic_parameters.model_dump(exclude_none=True)

    if isinstance(semantic_parameters, Mapping):
        return {
            key: value
            for key, value in semantic_parameters.items()
            if value is not None
        }

    return dict(semantic_parameters)


def _clean_string(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip().lower()
    return " ".join(text.split())


def _compile_time_range(time_range: str, today: date) -> list[str]:
    normalized = time_range.strip().lower().replace(" ", "_")

    if normalized == "today":
        return [f"after:{today:%Y/%m/%d}"]

    if normalized == "yesterday":
        yesterday = today - timedelta(days=1)
        return [f"after:{yesterday:%Y/%m/%d}", f"before:{today:%Y/%m/%d}"]

    if normalized == "this_week":
        start_of_week = today - timedelta(days=today.weekday())
        return [f"after:{start_of_week:%Y/%m/%d}"]

    if normalized == "last_week":
        start_of_this_week = today - timedelta(days=today.weekday())
        start_of_last_week = start_of_this_week - timedelta(days=7)
        return [
            f"after:{start_of_last_week:%Y/%m/%d}",
            f"before:{start_of_this_week:%Y/%m/%d}",
        ]

    if normalized == "this_month":
        start_of_month = today.replace(day=1)
        return [f"after:{start_of_month:%Y/%m/%d}"]

    if normalized == "last_month":
        start_of_this_month = today.replace(day=1)
        last_month_day = start_of_this_month - timedelta(days=1)
        start_of_last_month = last_month_day.replace(day=1)
        return [
            f"after:{start_of_last_month:%Y/%m/%d}",
            f"before:{start_of_this_month:%Y/%m/%d}",
        ]

    return []