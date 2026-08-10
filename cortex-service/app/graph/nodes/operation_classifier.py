from __future__ import annotations

import logging
from typing import Any

from app.core.execution_plan import ExecutionPlan
from app.core.gmail_query_compiler import compile_gmail_query
from app.core.operation_planner import (
    GmailQueryConstraints,
    PlannedOperation,
    generate_operation_plan,
)
from app.core.operations import OperationType
from app.graph.state import AgentState

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

    for operation in planned.operations:
        plan.add_operation(
            operation.operation,
            operation.connector,
            _compiled_operation_parameters(operation),
            depends_on=operation.depends_on,
        )

    _log_plan(
        question,
        plan,
    )

    return plan


def _compiled_operation_parameters(
    operation: PlannedOperation,
) -> dict[str, Any]:
    if isinstance(operation.parameters, GmailQueryConstraints):
        parameters: dict[str, Any] = operation.parameters.model_dump(
            exclude_none=True
        )
    else:
        parameters = dict(operation.parameters)

    parameters.pop("depends_on", None)

    if (
        operation.connector == "gmail"
        and operation.operation in {
            OperationType.SEARCH,
            OperationType.COUNT,
            OperationType.AGGREGATE,
        }
    ):
        compiled_parameters = parameters.copy()
        from datetime import date
        compiled_parameters["query"] = compile_gmail_query(parameters, today_override=date.today())
        return compiled_parameters

    return parameters


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