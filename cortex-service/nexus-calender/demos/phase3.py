import json
from datetime import datetime

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime_utils import DateTimeNormalizer


REFERENCE = datetime(
    2026,
    8,
    11,
    10,
    0,
)

normalizer = DateTimeNormalizer(
    "Asia/Kolkata"
)


TEST_CASES = [
    {
        "question": "Show my events today",
        "date": "today",
    },
    {
        "question": "Show my events tomorrow",
        "date": "tomorrow",
    },
    {
        "question": "Show my events yesterday",
        "date": "yesterday",
    },
    {
        "question": "Show my events this week",
        "date": "this week",
    },
    {
        "question": "Show my events last week",
        "date": "last week",
    },
    {
        "question": "Show my events next week",
        "date": "next week",
    },
    {
        "question": "Show my events this month",
        "date": "this month",
    },
    {
        "question": "Show my events last month",
        "date": "last month",
    },
    {
        "question": "Show my events next month",
        "date": "next month",
    },
    {
        "question": "Show my events last 7 days",
        "date": "last 7 days",
    },
    {
        "question": "Show my events next 7 days",
        "date": "next 7 days",
    },
    {
        "question": "Show my events last 3 months",
        "date": "last 3 months",
    },
    {
        "question": "Show my events next 3 months",
        "date": "next 3 months",
    },
    {
        "question": "Show my events last 2 years",
        "date": "last 2 years",
    },
    {
        "question": "Show my events next 2 years",
        "date": "next 2 years",
    },
    {
        "question": "Show my Friday events",
        "date": "Friday",
    },
    {
        "question": "Show my next Friday events",
        "date": "next Friday",
    },
    {
        "question": "Show events on August 20",
        "date": "2026-08-20",
    },
]


def normalize_case(case: dict) -> dict:
    expression = case["date"]

    result = normalizer.normalize_date_expression(
        expression,
        reference=REFERENCE,
    )

    return {
        "question": case["question"],
        "input": {
            "date": expression,
            "timezone": "Asia/Kolkata",
        },
        "normalized": {
            "start": result.start.isoformat(),
            "end": result.end.isoformat(),
        },
    }


def main():
    results = []

    for case in TEST_CASES:
        try:
            results.append(
                normalize_case(case)
            )
        except Exception as exc:
            results.append(
                {
                    "question": case["question"],
                    "input": {
                        "date": case["date"],
                        "timezone": "Asia/Kolkata",
                    },
                    "error": str(exc),
                }
            )

    print(
        json.dumps(
            results,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()