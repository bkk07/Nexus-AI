from __future__ import annotations

import logging
from typing import Any

from app.graph.state import AgentState


logger = logging.getLogger(__name__)


def operation_result_adapter_node(
    state: AgentState,
) -> dict[str, Any]:
    """
    Adapts results produced by the new operation executor
    into the existing AgentState representation.

    SEARCH results are exposed as raw_evidence so the
    existing collector/ranker/evaluator pipeline can
    continue working.

    Other operation results remain in operation_results.
    """

    operation_results = state.get(
        "operation_results",
        {},
    )

    logger.info(
        "[RESULT_ADAPTER] operation_result_keys=%s",
        list(operation_results.keys()),
    )

    if not operation_results:
        logger.info("[RESULT_ADAPTER] search_result_count=0")
        logger.info("[RESULT_ADAPTER] raw_evidence_count=0")
        return {
            "raw_evidence": [],
        }

    search_results = operation_results.get(
        "search",
        [],
    )

    if not isinstance(search_results, list):
        search_results = []

    logger.info(
        "[RESULT_ADAPTER] search_result_count=%s",
        len(search_results),
    )

    raw_evidence = []

    for email in search_results:

        if not isinstance(email, dict):
            continue

        raw_evidence.append(
            {
                "content": email.get(
                    "snippet",
                    "",
                ),

                "source": "gmail",

                "score": 0.0,

                "normalized_score": 0.0,

                "source_type": "gmail",

                "source_ref_id": email.get(
                    "id",
                ),

                "metadata": {
                    "from": email.get(
                        "from",
                    ),

                    "to": email.get(
                        "to",
                    ),

                    "subject": email.get(
                        "subject",
                    ),

                    "date": email.get(
                        "date",
                    ),

                    "thread_id": email.get(
                        "thread_id",
                    ),

                    "labels": email.get(
                        "labels",
                        [],
                    ),
                },
            }
        )

    logger.info(
        "[RESULT_ADAPTER] raw_evidence_count=%s",
        len(raw_evidence),
    )

    return {
        "raw_evidence": raw_evidence,
    }