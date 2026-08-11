from datetime import datetime

import pytest

from datetime_utils import DateTimeNormalizer


REFERENCE = datetime(
    2026,
    8,
    11,
    10,
    0,
)


@pytest.fixture
def normalizer():
    return DateTimeNormalizer(
        "Asia/Kolkata"
    )


def assert_range(
    result,
    start: str,
    end: str,
):
    assert result.start.isoformat() == start
    assert result.end.isoformat() == end


# =========================================================
# BASIC DAYS
# =========================================================


def test_today(normalizer):
    result = normalizer.normalize_date_expression(
        "today",
        reference=REFERENCE,
    )

    assert_range(
        result,
        "2026-08-11T00:00:00+05:30",
        "2026-08-12T00:00:00+05:30",
    )


def test_tomorrow(normalizer):
    result = normalizer.normalize_date_expression(
        "tomorrow",
        reference=REFERENCE,
    )

    assert_range(
        result,
        "2026-08-12T00:00:00+05:30",
        "2026-08-13T00:00:00+05:30",
    )


def test_yesterday(normalizer):
    result = normalizer.normalize_date_expression(
        "yesterday",
        reference=REFERENCE,
    )

    assert_range(
        result,
        "2026-08-10T00:00:00+05:30",
        "2026-08-11T00:00:00+05:30",
    )


# =========================================================
# WEEKS
# =========================================================


def test_this_week(normalizer):
    result = normalizer.normalize_date_expression(
        "this week",
        reference=REFERENCE,
    )

    assert_range(
        result,
        "2026-08-10T00:00:00+05:30",
        "2026-08-17T00:00:00+05:30",
    )


def test_last_week(normalizer):
    result = normalizer.normalize_date_expression(
        "last week",
        reference=REFERENCE,
    )

    assert_range(
        result,
        "2026-08-03T00:00:00+05:30",
        "2026-08-10T00:00:00+05:30",
    )


def test_next_week(normalizer):
    result = normalizer.normalize_date_expression(
        "next week",
        reference=REFERENCE,
    )

    assert_range(
        result,
        "2026-08-17T00:00:00+05:30",
        "2026-08-24T00:00:00+05:30",
    )


# =========================================================
# MONTHS
# =========================================================


def test_this_month(normalizer):
    result = normalizer.normalize_date_expression(
        "this month",
        reference=REFERENCE,
    )

    assert_range(
        result,
        "2026-08-01T00:00:00+05:30",
        "2026-09-01T00:00:00+05:30",
    )


def test_last_month(normalizer):
    result = normalizer.normalize_date_expression(
        "last month",
        reference=REFERENCE,
    )

    assert_range(
        result,
        "2026-07-01T00:00:00+05:30",
        "2026-08-01T00:00:00+05:30",
    )


def test_next_month(normalizer):
    result = normalizer.normalize_date_expression(
        "next month",
        reference=REFERENCE,
    )

    assert_range(
        result,
        "2026-09-01T00:00:00+05:30",
        "2026-10-01T00:00:00+05:30",
    )


# =========================================================
# YEARS
# =========================================================


def test_this_year(normalizer):
    result = normalizer.normalize_date_expression(
        "this year",
        reference=REFERENCE,
    )

    assert_range(
        result,
        "2026-01-01T00:00:00+05:30",
        "2027-01-01T00:00:00+05:30",
    )


def test_last_year(normalizer):
    result = normalizer.normalize_date_expression(
        "last year",
        reference=REFERENCE,
    )

    assert_range(
        result,
        "2025-01-01T00:00:00+05:30",
        "2026-01-01T00:00:00+05:30",
    )


def test_next_year(normalizer):
    result = normalizer.normalize_date_expression(
        "next year",
        reference=REFERENCE,
    )

    assert_range(
        result,
        "2027-01-01T00:00:00+05:30",
        "2028-01-01T00:00:00+05:30",
    )


# =========================================================
# LAST N DAYS
# =========================================================


@pytest.mark.parametrize(
    ("expression", "start", "end"),
    [
        (
            "last 1 day",
            "2026-08-11T00:00:00+05:30",
            "2026-08-12T00:00:00+05:30",
        ),
        (
            "last 7 days",
            "2026-08-05T00:00:00+05:30",
            "2026-08-12T00:00:00+05:30",
        ),
        (
            "last 17 days",
            "2026-07-26T00:00:00+05:30",
            "2026-08-12T00:00:00+05:30",
        ),
        (
            "last 30 days",
            "2026-07-13T00:00:00+05:30",
            "2026-08-12T00:00:00+05:30",
        ),
        (
            "last 100 days",
            "2026-05-04T00:00:00+05:30",
            "2026-08-12T00:00:00+05:30",
        ),
    ],
)
def test_last_n_days(
    normalizer,
    expression,
    start,
    end,
):
    result = normalizer.normalize_date_expression(
        expression,
        reference=REFERENCE,
    )

    assert_range(
        result,
        start,
        end,
    )


# =========================================================
# NEXT N DAYS
# =========================================================


@pytest.mark.parametrize(
    ("expression", "start", "end"),
    [
        (
            "next 1 day",
            "2026-08-11T00:00:00+05:30",
            "2026-08-12T00:00:00+05:30",
        ),
        (
            "next 7 days",
            "2026-08-11T00:00:00+05:30",
            "2026-08-18T00:00:00+05:30",
        ),
        (
            "next 17 days",
            "2026-08-11T00:00:00+05:30",
            "2026-08-28T00:00:00+05:30",
        ),
        (
            "next 30 days",
            "2026-08-11T00:00:00+05:30",
            "2026-09-10T00:00:00+05:30",
        ),
    ],
)
def test_next_n_days(
    normalizer,
    expression,
    start,
    end,
):
    result = normalizer.normalize_date_expression(
        expression,
        reference=REFERENCE,
    )

    assert_range(
        result,
        start,
        end,
    )


# =========================================================
# LAST N WEEKS
# =========================================================


@pytest.mark.parametrize(
    ("expression", "start", "end"),
    [
        (
            "last 1 week",
            "2026-08-04T00:00:00+05:30",
            "2026-08-12T00:00:00+05:30",
        ),
        (
            "last 2 weeks",
            "2026-07-28T00:00:00+05:30",
            "2026-08-12T00:00:00+05:30",
        ),
        (
            "last 5 weeks",
            "2026-07-07T00:00:00+05:30",
            "2026-08-12T00:00:00+05:30",
        ),
    ],
)
def test_last_n_weeks(
    normalizer,
    expression,
    start,
    end,
):
    result = normalizer.normalize_date_expression(
        expression,
        reference=REFERENCE,
    )

    assert_range(
        result,
        start,
        end,
    )


# =========================================================
# NEXT N WEEKS
# =========================================================


@pytest.mark.parametrize(
    ("expression", "start", "end"),
    [
        (
            "next 1 week",
            "2026-08-11T00:00:00+05:30",
            "2026-08-18T00:00:00+05:30",
        ),
        (
            "next 3 weeks",
            "2026-08-11T00:00:00+05:30",
            "2026-09-01T00:00:00+05:30",
        ),
        (
            "next 10 weeks",
            "2026-08-11T00:00:00+05:30",
            "2026-10-20T00:00:00+05:30",
        ),
    ],
)
def test_next_n_weeks(
    normalizer,
    expression,
    start,
    end,
):
    result = normalizer.normalize_date_expression(
        expression,
        reference=REFERENCE,
    )

    assert_range(
        result,
        start,
        end,
    )


# =========================================================
# LAST N MONTHS
# =========================================================


@pytest.mark.parametrize(
    ("expression", "start", "end"),
    [
        (
            "last 1 month",
            "2026-07-12T00:00:00+05:30",
            "2026-08-12T00:00:00+05:30",
        ),
        (
            "last 3 months",
            "2026-05-12T00:00:00+05:30",
            "2026-08-12T00:00:00+05:30",
        ),
        (
            "last 6 months",
            "2026-02-12T00:00:00+05:30",
            "2026-08-12T00:00:00+05:30",
        ),
    ],
)
def test_last_n_months(
    normalizer,
    expression,
    start,
    end,
):
    result = normalizer.normalize_date_expression(
        expression,
        reference=REFERENCE,
    )

    assert_range(
        result,
        start,
        end,
    )


# =========================================================
# NEXT N MONTHS
# =========================================================


@pytest.mark.parametrize(
    ("expression", "start", "end"),
    [
        (
            "next 1 month",
            "2026-08-11T00:00:00+05:30",
            "2026-09-11T00:00:00+05:30",
        ),
        (
            "next 3 months",
            "2026-08-11T00:00:00+05:30",
            "2026-11-11T00:00:00+05:30",
        ),
        (
            "next 12 months",
            "2026-08-11T00:00:00+05:30",
            "2027-08-11T00:00:00+05:30",
        ),
    ],
)
def test_next_n_months(
    normalizer,
    expression,
    start,
    end,
):
    result = normalizer.normalize_date_expression(
        expression,
        reference=REFERENCE,
    )

    assert_range(
        result,
        start,
        end,
    )


# =========================================================
# LAST N YEARS
# =========================================================


@pytest.mark.parametrize(
    ("expression", "start", "end"),
    [
        (
            "last 1 year",
            "2025-08-11T00:00:00+05:30",
            "2026-08-11T00:00:00+05:30",
        ),
        (
            "last 2 years",
            "2024-08-11T00:00:00+05:30",
            "2026-08-11T00:00:00+05:30",
        ),
        (
            "last 5 years",
            "2021-08-11T00:00:00+05:30",
            "2026-08-11T00:00:00+05:30",
        ),
    ],
)
def test_last_n_years(
    normalizer,
    expression,
    start,
    end,
):
    result = normalizer.normalize_date_expression(
        expression,
        reference=REFERENCE,
    )

    assert_range(
        result,
        start,
        end,
    )


# =========================================================
# NEXT N YEARS
# =========================================================


@pytest.mark.parametrize(
    ("expression", "start", "end"),
    [
        (
            "next 1 year",
            "2026-08-11T00:00:00+05:30",
            "2027-08-11T00:00:00+05:30",
        ),
        (
            "next 2 years",
            "2026-08-11T00:00:00+05:30",
            "2028-08-11T00:00:00+05:30",
        ),
        (
            "next 10 years",
            "2026-08-11T00:00:00+05:30",
            "2036-08-11T00:00:00+05:30",
        ),
    ],
)
def test_next_n_years(
    normalizer,
    expression,
    start,
    end,
):
    result = normalizer.normalize_date_expression(
        expression,
        reference=REFERENCE,
    )

    assert_range(
        result,
        start,
        end,
    )


# =========================================================
# WEEKDAYS
# =========================================================


@pytest.mark.parametrize(
    ("expression", "start", "end"),
    [
        (
            "monday",
            "2026-08-17T00:00:00+05:30",
            "2026-08-18T00:00:00+05:30",
        ),
        (
            "tuesday",
            "2026-08-11T00:00:00+05:30",
            "2026-08-12T00:00:00+05:30",
        ),
        (
            "friday",
            "2026-08-14T00:00:00+05:30",
            "2026-08-15T00:00:00+05:30",
        ),
        (
            "sunday",
            "2026-08-16T00:00:00+05:30",
            "2026-08-17T00:00:00+05:30",
        ),
    ],
)
def test_weekdays(
    normalizer,
    expression,
    start,
    end,
):
    result = normalizer.normalize_date_expression(
        expression,
        reference=REFERENCE,
    )

    assert_range(
        result,
        start,
        end,
    )


def test_next_friday(normalizer):
    result = normalizer.normalize_date_expression(
        "next friday",
        reference=REFERENCE,
    )

    assert_range(
        result,
        "2026-08-14T00:00:00+05:30",
        "2026-08-15T00:00:00+05:30",
    )


# =========================================================
# EXPLICIT ISO DATE
# =========================================================


def test_explicit_iso_date(normalizer):
    result = normalizer.normalize_date_expression(
        "2026-08-20",
        reference=REFERENCE,
    )

    assert_range(
        result,
        "2026-08-20T00:00:00+05:30",
        "2026-08-21T00:00:00+05:30",
    )


# =========================================================
# WHITESPACE / CASE
# =========================================================


def test_expression_is_normalized(
    normalizer,
):
    result = normalizer.normalize_date_expression(
        "   LAST   17   DAYS   ",
        reference=REFERENCE,
    )

    assert_range(
        result,
        "2026-07-26T00:00:00+05:30",
        "2026-08-12T00:00:00+05:30",
    )


# =========================================================
# TIMEZONE
# =========================================================


def test_timezone_is_attached_to_naive_reference(
    normalizer,
):
    result = normalizer.normalize_date_expression(
        "today",
        reference=REFERENCE,
    )

    assert result.start.tzinfo is not None
    assert result.end.tzinfo is not None

    assert result.start.isoformat() == (
        "2026-08-11T00:00:00+05:30"
    )


def test_aware_reference_is_converted():
    normalizer = DateTimeNormalizer(
        "Asia/Kolkata"
    )

    reference = datetime.fromisoformat(
        "2026-08-11T10:00:00+00:00"
    )

    result = normalizer.normalize_date_expression(
        "today",
        reference=reference,
    )

    assert result.start.isoformat() == (
        "2026-08-11T00:00:00+05:30"
    )


# =========================================================
# INVALID INPUT
# =========================================================


@pytest.mark.parametrize(
    "expression",
    [
        "",
        "   ",
        "some random date",
        "previous 7 days",
        "future 3 weeks",
        "last abc days",
        "next abc months",
        "last 0 days",
        "next 0 months",
    ],
)
def test_invalid_expression(
    normalizer,
    expression,
):
    with pytest.raises(ValueError):
        normalizer.normalize_date_expression(
            expression,
            reference=REFERENCE,
        )