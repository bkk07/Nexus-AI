from __future__ import annotations

import logging
from typing import Any

from app.core.operations import OperationType
from app.graph.state import AgentState
from app.connectors.gmail.connector import (
    build_default_gmail_connector,
)


logger = logging.getLogger(__name__)


def _summarize_operation_results(
    operation_results: dict[str, Any],
) -> dict[str, Any]:
    summary: dict[str, Any] = {}

    for key, value in operation_results.items():
        if isinstance(value, list):
            summary[key] = {
                "type": "list",
                "count": len(value),
            }
        elif isinstance(value, dict):
            summary[key] = {
                "type": "dict",
                "keys": list(value.keys()),
            }
        else:
            summary[key] = {
                "type": type(value).__name__,
                "value": value,
            }

    return summary


async def operation_executor_node(
    state: AgentState,
) -> dict[str, Any]:
    """
    Execute operations from AgentState.operation_plan.

    This node dispatches operations to the appropriate
    connector/service.

    Currently supported Gmail operations:

        SEARCH
        FETCH
        COUNT
        FILTER
        CLASSIFY
        EXTRACT

    SUMMARIZE is intentionally not executed here.
    It will be handled by the LLM/post-processing layer.
    """

    plan = state.get("operation_plan")

    if plan is None or plan.is_empty():
        return {
            "operation_results": {},
        }

    gmail = build_default_gmail_connector()

    operation_results: dict[str, Any] = {}

    for index, operation in enumerate(plan.operations):

        operation_type = operation.operation_type

        logger.info(
            "[OPERATION_EXECUTOR] operation_index=%s operation_type=%s connector=%s parameters=%s",
            index,
            operation_type.value,
            operation.connector,
            operation.parameters,
        )

        # ------------------------------------------------------
        # Gmail
        # ------------------------------------------------------

        if operation.connector == "gmail":

            # --------------------------------------------------
            # SEARCH
            # --------------------------------------------------

            if operation_type == OperationType.SEARCH:

                query = operation.parameters.get(
                    "query",
                    "",
                )

                top_k = operation.parameters.get(
                    "top_k",
                    10,
                )

                logger.debug("[OPERATION_EXECUTOR] SEARCH QUERY: %s", query)
                logger.debug("[OPERATION_EXECUTOR] SEARCH TOP_K: %s", top_k)

                result = await gmail.search(
                    query=query,
                    top_k=top_k,
                )

                logger.debug(
                    "[OPERATION_EXECUTOR] SEARCH RESULT_COUNT: %s",
                    len(result),
                )

                operation_results[
                    operation_type.value.lower()
                ] = result

            # --------------------------------------------------
            # FETCH
            # --------------------------------------------------

            elif operation_type == OperationType.FETCH:

                source = operation.parameters.get(
                    "source",
                )

                # For now FETCH expects the previous
                # SEARCH result.
                previous_result = None

                if (
                    source == "previous_operation"
                    and index > 0
                ):
                    previous_operation = (
                        plan.operations[index - 1]
                    )

                    previous_key = (
                        previous_operation
                        .operation_type
                        .value
                        .lower()
                    )

                    previous_result = (
                        operation_results.get(
                            previous_key
                        )
                    )

                if not previous_result:
                    operation_results[
                        operation_type.value.lower()
                    ] = []

                    continue

                fetched = []

                for email in previous_result:

                    message_id = email.get("id")

                    if not message_id:
                        continue

                    logger.debug(
                        "[OPERATION_EXECUTOR] FETCH MESSAGE_ID: %s",
                        message_id,
                    )

                    try:
                        fetched_email = await gmail.fetch(message_id)
                    except Exception:
                        logger.exception(
                            "[OPERATION_EXECUTOR] FETCH RESULT: failure"
                        )
                        raise

                    body = fetched_email.get("body", "")
                    body_length = len(body) if isinstance(body, str) else 0

                    logger.debug(
                        "[OPERATION_EXECUTOR] FETCH RESULT: success"
                    )
                    logger.debug(
                        "[OPERATION_EXECUTOR] FETCH BODY_LENGTH: %s",
                        body_length,
                    )

                    fetched.append(
                        fetched_email
                    )

                operation_results[
                    operation_type.value.lower()
                ] = fetched

            # --------------------------------------------------
            # COUNT
            # --------------------------------------------------

            elif operation_type == OperationType.COUNT:

                query = operation.parameters.get(
                    "query",
                    "",
                )

                logger.debug("[OPERATION_EXECUTOR] COUNT QUERY: %s", query)

                count = await gmail.count(
                    query=query,
                )

                logger.debug(
                    "[OPERATION_EXECUTOR] COUNT RESULT: %s",
                    count,
                )

                operation_results[
                    operation_type.value.lower()
                ] = count

            # --------------------------------------------------
            # FILTER
            # --------------------------------------------------

            elif operation_type == OperationType.FILTER:

                source = operation.parameters.get(
                    "source",
                )

                previous_result = None

                if (
                    source == "previous_operation"
                    and index > 0
                ):
                    previous_operation = (
                        plan.operations[index - 1]
                    )

                    previous_key = (
                        previous_operation
                        .operation_type
                        .value
                        .lower()
                    )

                    previous_result = (
                        operation_results.get(
                            previous_key
                        )
                    )

                if previous_result is None:
                    previous_result = []

                field = operation.parameters.get(
                    "field",
                    "subject",
                )

                operator = operation.parameters.get(
                    "operator",
                    "contains",
                )

                value = operation.parameters.get(
                    "value",
                    "",
                )

                filtered = gmail.filter_emails(
                    emails=previous_result,
                    field=field,
                    operator=operator,
                    value=value,
                )

                operation_results[
                    operation_type.value.lower()
                ] = filtered

            # --------------------------------------------------
            # CLASSIFY
            # --------------------------------------------------

            elif operation_type == OperationType.CLASSIFY:

                source = operation.parameters.get(
                    "source",
                )

                previous_result = None

                if (
                    source == "previous_operation"
                    and index > 0
                ):
                    previous_operation = (
                        plan.operations[index - 1]
                    )

                    previous_key = (
                        previous_operation
                        .operation_type
                        .value
                        .lower()
                    )

                    previous_result = (
                        operation_results.get(
                            previous_key
                        )
                    )

                if previous_result is None:
                    previous_result = []

                classified = gmail.classify_emails(
                    previous_result
                )

                operation_results[
                    operation_type.value.lower()
                ] = classified

            # --------------------------------------------------
            # EXTRACT
            # --------------------------------------------------

            elif operation_type == OperationType.EXTRACT:

                source = operation.parameters.get(
                    "source",
                )

                previous_result = None

                if (
                    source == "previous_operation"
                    and index > 0
                ):
                    previous_operation = (
                        plan.operations[index - 1]
                    )

                    previous_key = (
                        previous_operation
                        .operation_type
                        .value
                        .lower()
                    )

                    previous_result = (
                        operation_results.get(
                            previous_key
                        )
                    )

                if previous_result is None:
                    previous_result = []

                fields = operation.parameters.get(
                    "fields",
                    [
                        "emails",
                        "urls",
                        "phones",
                    ],
                )

                extracted = []

                for email in previous_result:

                    extracted.append(
                        {
                            "id": email.get("id"),
                            "extracted": (
                                gmail.extract_information(
                                    email,
                                    fields,
                                )
                            ),
                        }
                    )

                operation_results[
                    operation_type.value.lower()
                ] = extracted

            # --------------------------------------------------
            # SUMMARIZE
            # --------------------------------------------------

            elif operation_type == OperationType.SUMMARIZE:

                operation_results[
                    operation_type.value.lower()
                ] = {
                    "status": "PENDING_LLM",
                    "source": operation.parameters.get(
                        "source"
                    ),
                }

            else:

                operation_results[
                    operation_type.value.lower()
                ] = {
                    "status": "UNSUPPORTED_OPERATION",
                    "operation": operation_type.value,
                }

        else:

            operation_results[
                operation_type.value.lower()
            ] = {
                "status": "UNSUPPORTED_CONNECTOR",
                "connector": operation.connector,
            }

    logger.info(
        "[OPERATION_EXECUTOR] completed_operations=%s result_keys=%s result_summary=%s",
        len(plan.operations),
        list(operation_results.keys()),
        _summarize_operation_results(operation_results),
    )

    return {
        "operation_results": operation_results,
    }