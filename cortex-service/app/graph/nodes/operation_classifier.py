from __future__ import annotations

import logging
import re

from app.core.operations import OperationType
from app.core.execution_plan import ExecutionPlan
from app.graph.state import AgentState
from app.core.operation_planner import (
    generate_operation_plan,
)

logger = logging.getLogger(__name__)


def _log_plan(question: str, plan: ExecutionPlan) -> None:
    logger.info("[OPERATION_CLASSIFIER] question=%r", question)
    logger.info(
        "[OPERATION_CLASSIFIER] complete_operation_plan=%s",
        [
            {
                "operation": operation.operation_type.value,
                "connector": operation.connector,
                "parameters": operation.parameters,
                "depends_on": operation.depends_on,
            }
            for operation in plan.operations
        ],
    )

def classify_operation(
    question: str,
) -> ExecutionPlan:
    """
    Uses the LLM operation planner to convert
    natural language into an ExecutionPlan.
    """

    plan = ExecutionPlan()

    planned = generate_operation_plan(
        question
    )

    normalized_operations = _normalize_planned_operations(
        question,
        planned.operations,
    )

    for operation in normalized_operations:

        parameters = dict(operation.parameters)
        depends_on = operation.depends_on

        if depends_on is None and "depends_on" in parameters:
            raw_depends_on = parameters.pop("depends_on")

            if isinstance(raw_depends_on, int):
                depends_on = raw_depends_on

        plan.add_operation(
            operation.operation,
            operation.connector,
            parameters,
            depends_on=depends_on,
        )

    _log_plan(
        question,
        plan,
    )

    return plan

def _extract_gmail_query(
    text: str,
) -> str:
    """
    First deterministic version.

    We intentionally keep this simple.
    The Gmail query compiler can later translate
    richer natural-language constraints.
    """

    normalized = text.lower().strip()

    terms: list[str] = []

    if "unread" in normalized:
        terms.append("is:unread")

    if "microsoft" in normalized:
        terms.append("from:(microsoft)")

    if "interview" in normalized:
        terms.append("interview")

    if "this week" in normalized or "latest" in normalized or "most recent" in normalized:
        terms.append("newer_than:7d")

    if "inbox" in normalized and "from:(microsoft)" not in terms:
        terms.append("in:inbox")

    if not terms:
        terms.append("in:anywhere")

    return " ".join(dict.fromkeys(terms))


def _is_aggregate_question(text: str) -> bool:
    return bool(
        re.search(r"\b(most|breakdown|group by|who emailed me most|which sender emailed me the most)\b", text)
    )


def _is_count_question(text: str) -> bool:
    return bool(
        re.search(r"\b(how many|number of|count)\b", text)
    )


def _is_summarize_question(text: str) -> bool:
    return bool(
        re.search(r"\b(summarize|summary|summarise)\b", text)
    )


def _is_extract_question(text: str) -> bool:
    return bool(
        re.search(r"\b(extract|find the phone|find the email address|find the url)\b", text)
    )


def _is_classify_question(text: str) -> bool:
    return bool(
        re.search(r"\b(classify|categorize|category|type of email)\b", text)
    )


def _explicit_full_content_request(text: str) -> bool:
    return bool(
        re.search(r"\b(open|read|show me the full|full email)\b", text)
    )


def _search_top_k(question: str) -> int:
    normalized = question.lower()

    if "latest" in normalized or "most recent" in normalized:
        return 1

    return 10


def _normalize_planned_operations(
    question: str,
    planned_operations,
):
    normalized = question.lower().strip()

    if _is_count_question(normalized):
        return [
            _build_operation(
                OperationType.COUNT,
                "gmail",
                {
                    "query": _extract_gmail_query(normalized),
                },
            )
        ]

    if _is_aggregate_question(normalized):
        return [
            _build_operation(
                OperationType.AGGREGATE,
                "gmail",
                {
                    "query": _extract_gmail_query(normalized),
                },
            )
        ]

    if _is_summarize_question(normalized):
        return [
            _build_operation(
                OperationType.SEARCH,
                "gmail",
                {
                    "query": _extract_gmail_query(normalized),
                    "top_k": _search_top_k(normalized),
                },
            ),
            _build_operation(
                OperationType.FETCH,
                "gmail",
                {
                    "source": "previous_operation",
                },
                depends_on=0,
            ),
            _build_operation(
                OperationType.SUMMARIZE,
                "llm",
                {
                    "source": "previous_operation",
                },
                depends_on=1,
            ),
        ]

    if _is_extract_question(normalized):
        return [
            _build_operation(
                OperationType.SEARCH,
                "gmail",
                {
                    "query": _extract_gmail_query(normalized),
                    "top_k": _search_top_k(normalized),
                },
            ),
            _build_operation(
                OperationType.FETCH,
                "gmail",
                {
                    "source": "previous_operation",
                },
                depends_on=0,
            ),
            _build_operation(
                OperationType.EXTRACT,
                "gmail",
                {
                    "source": "previous_operation",
                },
                depends_on=1,
            ),
        ]

    if _is_classify_question(normalized):
        return [
            _build_operation(
                OperationType.SEARCH,
                "gmail",
                {
                    "query": _extract_gmail_query(normalized),
                    "top_k": _search_top_k(normalized),
                },
            ),
            _build_operation(
                OperationType.CLASSIFY,
                "gmail",
                {
                    "source": "previous_operation",
                },
                depends_on=0,
            ),
        ]

    if _explicit_full_content_request(normalized):
        return [
            _build_operation(
                OperationType.SEARCH,
                "gmail",
                {
                    "query": _extract_gmail_query(normalized),
                    "top_k": _search_top_k(normalized),
                },
            ),
            _build_operation(
                OperationType.FETCH,
                "gmail",
                {
                    "source": "previous_operation",
                },
                depends_on=0,
            ),
        ]

    return [
        _build_operation(
            OperationType.SEARCH,
            "gmail",
            {
                "query": _extract_gmail_query(normalized),
                "top_k": _search_top_k(normalized),
            },
        )
    ]


def _build_operation(
    operation_type: OperationType,
    connector: str,
    parameters: dict,
    depends_on: int | None = None,
):
    class _OperationLike:
        def __init__(self):
            self.operation = operation_type
            self.connector = connector
            self.parameters = parameters
            self.depends_on = depends_on

    return _OperationLike()


def _log_plan(question: str, plan: ExecutionPlan) -> None:
    logger.info("[OPERATION_CLASSIFIER] question=%r", question)
    logger.info(
        "[OPERATION_CLASSIFIER] complete_operation_plan=%s",
        [
            {
                "operation": operation.operation_type.value,
                "connector": operation.connector,
                "parameters": operation.parameters,
                "depends_on": operation.depends_on,
            }
            for operation in plan.operations
        ],
    )
def operation_classifier_node(
    state: AgentState,
) -> AgentState:

    question = state.get(
        "question",
        "",
    ).strip()

    if not question:
        logger.debug(
            "[OPERATION_CLASSIFIER] empty question"
        )

        return {
            **state,
            "operation_plan": None,
            "operation_results": {},
        }

    plan = classify_operation(
        question
    )

    return {
        **state,
        "operation_plan": plan,
        "operation_results": {},
    }