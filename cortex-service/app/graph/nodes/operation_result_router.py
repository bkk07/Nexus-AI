from __future__ import annotations

import logging

from app.core.operations import OperationType
from app.graph.state import AgentState


logger = logging.getLogger(__name__)


def route_after_operation_execution(
    state: AgentState,
) -> str:
    """
    Decide what should happen after operation execution.

    SEARCH:
        Continue through the existing evidence pipeline.

    COUNT / AGGREGATE:
        Go directly to the final response path.

    FETCH:
        Go to the final response path for now.

    SUMMARIZE:
        Go to the final response path where the LLM
        summarization layer will consume the fetched content.

    Other operations:
        Go to the final response path.
    """

    plan = state.get("operation_plan")

    if plan is None or plan.is_empty():
        logger.info(
            "[RESULT_ROUTER] final_operation=NONE route=generator_node"
        )
        return "generator_node"

    operations = plan.operations

    # The final operation represents what the user
    # ultimately wants.
    final_operation = operations[-1]

    operation_type = final_operation.operation_type

    if operation_type == OperationType.SEARCH:
        logger.info(
            "[RESULT_ROUTER] final_operation=%s route=operation_result_adapter_node",
            operation_type.value,
        )
        return "operation_result_adapter_node"

    if operation_type in {
        OperationType.COUNT,
        OperationType.AGGREGATE,
        OperationType.FETCH,
        OperationType.SUMMARIZE,
        OperationType.FILTER,
        OperationType.CLASSIFY,
        OperationType.EXTRACT,
    }:
        logger.info(
            "[RESULT_ROUTER] final_operation=%s route=generator_node",
            operation_type.value,
        )
        return "generator_node"

    logger.info(
        "[RESULT_ROUTER] final_operation=%s route=generator_node",
        operation_type.value,
    )
    return "generator_node"