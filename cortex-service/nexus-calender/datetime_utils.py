from __future__ import annotations

import re
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class DateTimeRange:
    """
    Half-open datetime range:

        [start, end)

    start is inclusive.
    end is exclusive.
    """

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None:
            raise ValueError(
                "Range start must be timezone-aware."
            )

        if self.end.tzinfo is None:
            raise ValueError(
                "Range end must be timezone-aware."
            )

        if self.end <= self.start:
            raise ValueError(
                "Range end must be after range start."
            )


class DateTimeNormalizer:
    """
    Deterministic temporal expression normalizer.

    Converts semantic expressions such as:

        today
        tomorrow
        this week
        last 7 days
        next 3 weeks
        last 6 months
        next 2 years
        Friday
        next Friday
        this month
        last year

    into timezone-aware datetime ranges.

    No LLM is used here.
    """

    _RELATIVE_PATTERN = re.compile(
        r"^(last|next)\s+(\d+)\s+"
        r"(day|days|week|weeks|month|months|year|years)$"
    )

    _WEEKDAYS = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    def __init__(
        self,
        timezone: str = "Asia/Kolkata",
    ) -> None:
        self.timezone = ZoneInfo(timezone)

    # =========================================================
    # PUBLIC API
    # =========================================================

    def normalize_date_expression(
        self,
        expression: str,
        *,
        reference: datetime,
    ) -> DateTimeRange:

        if not expression or not expression.strip():
            raise ValueError(
                "Date expression cannot be empty."
            )

        reference = self._ensure_timezone(reference)

        expression = self._clean_expression(
            expression
        )

        current_date = reference.date()

        # -----------------------------------------------------
        # Fixed relative expressions
        # -----------------------------------------------------

        if expression == "today":
            return self._day_range(current_date)

        if expression == "tomorrow":
            return self._day_range(
                current_date + timedelta(days=1)
            )

        if expression == "yesterday":
            return self._day_range(
                current_date - timedelta(days=1)
            )

        # -----------------------------------------------------
        # Fixed week expressions
        # -----------------------------------------------------

        if expression == "this week":
            return self._this_week(current_date)

        if expression == "last week":
            return self._last_week(current_date)

        if expression == "next week":
            return self._next_week(current_date)

        # -----------------------------------------------------
        # Fixed month expressions
        # -----------------------------------------------------

        if expression == "this month":
            return self._this_month(current_date)

        if expression == "last month":
            return self._last_month(current_date)

        if expression == "next month":
            return self._next_month(current_date)

        # -----------------------------------------------------
        # Fixed year expressions
        # -----------------------------------------------------

        if expression == "this year":
            return self._this_year(current_date)

        if expression == "last year":
            return self._last_year(current_date)

        if expression == "next year":
            return self._next_year(current_date)

        # -----------------------------------------------------
        # Generic relative expressions
        # -----------------------------------------------------

        relative_match = self._RELATIVE_PATTERN.fullmatch(
            expression
        )

        if relative_match:
            direction = relative_match.group(1)
            amount = int(relative_match.group(2))
            unit = relative_match.group(3)

            return self._relative_range(
                current_date=current_date,
                direction=direction,
                amount=amount,
                unit=unit,
            )

        # -----------------------------------------------------
        # Weekdays
        # -----------------------------------------------------

        weekday = self._parse_weekday(
            expression
        )

        if weekday is not None:
            target = self._next_weekday(
                current_date,
                weekday,
            )

            return self._day_range(target)

        # -----------------------------------------------------
        # Explicit ISO date
        # -----------------------------------------------------

        explicit_date = self._parse_iso_date(
            expression
        )

        if explicit_date is not None:
            return self._day_range(
                explicit_date
            )

        raise ValueError(
            f"Unsupported date expression: "
            f"{expression!r}"
        )

    # =========================================================
    # GENERIC RELATIVE RANGES
    # =========================================================

    def _relative_range(
        self,
        *,
        current_date: date,
        direction: str,
        amount: int,
        unit: str,
    ) -> DateTimeRange:

        if amount <= 0:
            raise ValueError(
                "Relative range amount must be positive."
            )

        # -----------------------------------------------------
        # DAYS
        # -----------------------------------------------------

        if unit in {"day", "days"}:

            if direction == "last":
                # Include the complete current day.
                end = current_date + timedelta(days=1)
                start = end - timedelta(days=amount)

            else:
                start = current_date
                end = start + timedelta(days=amount)

            return self._date_range(
                start,
                end,
            )

        # -----------------------------------------------------
        # WEEKS
        # -----------------------------------------------------

        if unit in {"week", "weeks"}:

            days = amount * 7

            if direction == "last":
                end = current_date + timedelta(days=1)
                start = end - timedelta(days=days + 1)

            else:
                start = current_date
                end = start + timedelta(days=days)

            return self._date_range(
                start,
                end,
            )
        
        # -----------------------------------------------------
        # MONTHS
        #
        # "last N months" means N calendar months ending
        # at the end of the current day.
        #
        # Example:
        #
        # reference = 2026-08-11
        #
        # last 1 month
        #   2026-07-12 -> 2026-08-12
        #
        # last 3 months
        #   2026-05-12 -> 2026-08-12
        # -----------------------------------------------------

        if unit in {"month", "months"}:

            if direction == "last":

                # Include the entire current day.
                end = current_date + timedelta(days=1)

                start = self._add_months(
                    end,
                    -amount,
                )

            else:

                start = current_date

                end = self._add_months(
                    start,
                    amount,
                )

            return self._date_range(
                start,
                end,
            )

        # -----------------------------------------------------
        # YEARS
        #
        # "last N years" means N calendar years ending
        # at the current date.
        #
        # Example:
        #
        # reference = 2026-08-11
        #
        # last 1 year
        #   2025-08-11 -> 2026-08-11
        #
        # last 2 years
        #   2024-08-11 -> 2026-08-11
        # -----------------------------------------------------

        if unit in {"year", "years"}:

            if direction == "last":

                end = current_date

                start = self._add_years(
                    end,
                    -amount,
                )

            else:

                start = current_date

                end = self._add_years(
                    start,
                    amount,
                )

            return self._date_range(
                start,
                end,
            )

        raise ValueError(
            f"Unsupported relative unit: {unit}"
        )

    # =========================================================
    # DAY
    # =========================================================

    def _day_range(
        self,
        target_date: date,
    ) -> DateTimeRange:

        start = datetime.combine(
            target_date,
            time.min,
            tzinfo=self.timezone,
        )

        end = start + timedelta(days=1)

        return DateTimeRange(
            start=start,
            end=end,
        )

    # =========================================================
    # WEEK
    # =========================================================

    def _this_week(
        self,
        current_date: date,
    ) -> DateTimeRange:

        monday = current_date - timedelta(
            days=current_date.weekday()
        )

        return self._week_range(monday)

    def _last_week(
        self,
        current_date: date,
    ) -> DateTimeRange:

        current_monday = current_date - timedelta(
            days=current_date.weekday()
        )

        previous_monday = (
            current_monday
            - timedelta(days=7)
        )

        return self._week_range(
            previous_monday
        )

    def _next_week(
        self,
        current_date: date,
    ) -> DateTimeRange:

        current_monday = current_date - timedelta(
            days=current_date.weekday()
        )

        next_monday = (
            current_monday
            + timedelta(days=7)
        )

        return self._week_range(
            next_monday
        )

    def _week_range(
        self,
        monday: date,
    ) -> DateTimeRange:

        start = datetime.combine(
            monday,
            time.min,
            tzinfo=self.timezone,
        )

        end = start + timedelta(days=7)

        return DateTimeRange(
            start=start,
            end=end,
        )

    # =========================================================
    # MONTH
    # =========================================================

    def _this_month(
        self,
        current_date: date,
    ) -> DateTimeRange:

        start = current_date.replace(day=1)

        end = self._add_months(
            start,
            1,
        )

        return self._date_range(
            start,
            end,
        )

    def _last_month(
        self,
        current_date: date,
    ) -> DateTimeRange:

        end = current_date.replace(day=1)

        start = self._add_months(
            end,
            -1,
        )

        return self._date_range(
            start,
            end,
        )

    def _next_month(
        self,
        current_date: date,
    ) -> DateTimeRange:

        start = current_date.replace(day=1)

        start = self._add_months(
            start,
            1,
        )

        end = self._add_months(
            start,
            1,
        )

        return self._date_range(
            start,
            end,
        )

    # =========================================================
    # YEAR
    # =========================================================

    def _this_year(
        self,
        current_date: date,
    ) -> DateTimeRange:

        start = date(
            current_date.year,
            1,
            1,
        )

        end = date(
            current_date.year + 1,
            1,
            1,
        )

        return self._date_range(
            start,
            end,
        )

    def _last_year(
        self,
        current_date: date,
    ) -> DateTimeRange:

        start = date(
            current_date.year - 1,
            1,
            1,
        )

        end = date(
            current_date.year,
            1,
            1,
        )

        return self._date_range(
            start,
            end,
        )

    def _next_year(
        self,
        current_date: date,
    ) -> DateTimeRange:

        start = date(
            current_date.year + 1,
            1,
            1,
        )

        end = date(
            current_date.year + 2,
            1,
            1,
        )

        return self._date_range(
            start,
            end,
        )

    # =========================================================
    # WEEKDAY
    # =========================================================

    def _parse_weekday(
        self,
        expression: str,
    ) -> int | None:

        if expression in self._WEEKDAYS:
            return self._WEEKDAYS[expression]

        if expression.startswith("next "):
            weekday_name = expression[5:].strip()

            if weekday_name in self._WEEKDAYS:
                return self._WEEKDAYS[
                    weekday_name
                ]

        return None

    def _next_weekday(
        self,
        current_date: date,
        target_weekday: int,
    ) -> date:

        days_ahead = (
            target_weekday
            - current_date.weekday()
        ) % 7

        return current_date + timedelta(
            days=days_ahead
        )

    # =========================================================
    # DATE PARSING
    # =========================================================

    @staticmethod
    def _parse_iso_date(
        expression: str,
    ) -> date | None:

        try:
            return date.fromisoformat(
                expression
            )
        except ValueError:
            return None

    # =========================================================
    # CALENDAR ARITHMETIC
    # =========================================================

    @staticmethod
    def _add_months(
        value: date,
        months: int,
    ) -> date:

        total_months = (
            value.year * 12
            + (value.month - 1)
            + months
        )

        year = total_months // 12

        month = (
            total_months % 12
        ) + 1

        last_day = monthrange(
            year,
            month,
        )[1]

        day = min(
            value.day,
            last_day,
        )

        return date(
            year,
            month,
            day,
        )

    @staticmethod
    def _add_years(
        value: date,
        years: int,
    ) -> date:

        target_year = value.year + years

        # Handle Feb 29 when target year is not leap.
        if (
            value.month == 2
            and value.day == 29
        ):
            if not (
                target_year % 4 == 0
                and (
                    target_year % 100 != 0
                    or target_year % 400 == 0
                )
            ):
                return date(
                    target_year,
                    2,
                    28,
                )

        return date(
            target_year,
            value.month,
            value.day,
        )

    # =========================================================
    # HELPERS
    # =========================================================

    def _date_range(
        self,
        start_date: date,
        end_date: date,
    ) -> DateTimeRange:

        start = datetime.combine(
            start_date,
            time.min,
            tzinfo=self.timezone,
        )

        end = datetime.combine(
            end_date,
            time.min,
            tzinfo=self.timezone,
        )

        return DateTimeRange(
            start=start,
            end=end,
        )

    @staticmethod
    def _clean_expression(
        expression: str,
    ) -> str:

        return " ".join(
            expression.lower().strip().split()
        )

    def _ensure_timezone(
        self,
        value: datetime,
    ) -> datetime:

        if value.tzinfo is None:
            return value.replace(
                tzinfo=self.timezone
            )

        return value.astimezone(
            self.timezone
        )