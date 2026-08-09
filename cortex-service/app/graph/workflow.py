from __future__ import annotations

import logging

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import AgentState

from app.graph.nodes import (
    intent_detection_node,
    collector_node,
    ranker_node,
    evaluator_node,
    query_rewriter_node,
    generator_node,
    simple_qa_node,
)

from app.graph.nodes.operation_classifier import (
    operation_classifier_node,
)

from app.graph.nodes.operation_executor import (
    operation_executor_node,
)

from app.graph.nodes.operation_result_adapter import (
    operation_result_adapter_node,
)

from app.graph.nodes.operation_result_router import (
    route_after_operation_execution,
)


logger = logging.getLogger(__name__)


def route_by_intent(state: AgentState) -> str:
    """
    Routes based on the initial query intent.

    Simple questions go directly to simple QA.

    Retrieval-required questions go through the
    operation planning/execution pipeline.
    """

    intent = state.get(
        "intent",
        "simple_qa",
    )

    if intent == "retrieval_needed":
        logger.info("[WORKFLOW] intent_detection -> operation_classifier")
        return "operation_classifier_node"

    logger.info("[WORKFLOW] intent_detection -> simple_qa")
    return "simple_qa_node"


def route_after_evaluator(state: AgentState) -> str:
    """
    Evaluates evidence relevance and manages rewrite retries.
    """

    is_relevant = state.get(
        "is_relevant",
        False,
    )

    retry_count = state.get(
        "retry_count",
        0,
    )

    if is_relevant:
        logger.info("[WORKFLOW] evaluator -> generator")
        return "generator_node"

    if retry_count < 2:
        logger.info("[WORKFLOW] evaluator -> query_rewriter")
        return "query_rewriter_node"

    logger.info("[WORKFLOW] evaluator -> generator")
    return "generator_node"


# ============================================================
# Build Graph
# ============================================================

workflow = StateGraph(AgentState)


# ============================================================
# Add Nodes
# ============================================================

workflow.add_node(
    "intent_detection_node",
    intent_detection_node,
)

workflow.add_node(
    "operation_classifier_node",
    operation_classifier_node,
)

workflow.add_node(
    "operation_executor_node",
    operation_executor_node,
)

workflow.add_node(
    "operation_result_adapter_node",
    operation_result_adapter_node,
)

workflow.add_node(
    "simple_qa_node",
    simple_qa_node,
)

workflow.add_node(
    "collector_node",
    collector_node,
)

workflow.add_node(
    "ranker_node",
    ranker_node,
)

workflow.add_node(
    "evaluator_node",
    evaluator_node,
)

workflow.add_node(
    "query_rewriter_node",
    query_rewriter_node,
)

workflow.add_node(
    "generator_node",
    generator_node,
)


# ============================================================
# Entry Point
# ============================================================

workflow.add_edge(
    START,
    "intent_detection_node",
)


# ============================================================
# Intent Routing
# ============================================================

workflow.add_conditional_edges(
    "intent_detection_node",
    route_by_intent,
    {
        "simple_qa_node": "simple_qa_node",
        "operation_classifier_node":
            "operation_classifier_node",
    },
)


# ============================================================
# NEW OPERATION PIPELINE
# ============================================================

workflow.add_edge(
    "operation_classifier_node",
    "operation_executor_node",
)


workflow.add_conditional_edges(
    "operation_executor_node",
    route_after_operation_execution,
    {
        "operation_result_adapter_node":
            "operation_result_adapter_node",

        "generator_node":
            "generator_node",
    },
)


# ============================================================
# SEARCH → EXISTING EVIDENCE PIPELINE
# ============================================================

workflow.add_edge(
    "operation_result_adapter_node",
    "collector_node",
)

workflow.add_edge(
    "collector_node",
    "ranker_node",
)

workflow.add_edge(
    "ranker_node",
    "evaluator_node",
)


# ============================================================
# Evaluator / Reflection Loop
# ============================================================

workflow.add_conditional_edges(
    "evaluator_node",
    route_after_evaluator,
    {
        "generator_node":
            "generator_node",

        "query_rewriter_node":
            "query_rewriter_node",
    },
)


# ============================================================
# Query Rewriter
# ============================================================

workflow.add_edge(
    "query_rewriter_node",
    "operation_classifier_node",
)


# ============================================================
# Output
# ============================================================

workflow.add_edge(
    "simple_qa_node",
    END,
)

workflow.add_edge(
    "generator_node",
    END,
)


# ============================================================
# Checkpointer
# ============================================================

checkpointer = MemorySaver()

rag_app = workflow.compile(
    checkpointer=checkpointer,
)