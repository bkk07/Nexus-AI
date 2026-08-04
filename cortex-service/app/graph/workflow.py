from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import AgentState
from app.graph.nodes import (
    intent_detection_node,
    planner_node,
    retriever_node,
    ranker_node,
    evaluator_node,
    query_rewriter_node,
    generator_node,
    simple_qa_node,
)


def route_by_intent(state: AgentState) -> str:
    intent = state.get("intent", "retrieval_needed")
    if intent == "simple_qa":
        return "simple_qa"
    return "planner"


def route_after_evaluation(state: AgentState) -> str:
    is_relevant = state.get("is_relevant", False)
    retry_count = state.get("retry_count", 0)

    if is_relevant or retry_count >= 2:
        return "generator"
    else:
        return "query_rewriter"


def build_graph():
    builder = StateGraph(AgentState)

    # Nodes
    builder.add_node("intent_detection", intent_detection_node)
    builder.add_node("simple_qa", simple_qa_node)
    builder.add_node("planner", planner_node)
    builder.add_node("retriever", retriever_node)
    builder.add_node("ranker", ranker_node)
    builder.add_node("evaluator", evaluator_node)
    builder.add_node("query_rewriter", query_rewriter_node)
    builder.add_node("generator", generator_node)

    # Edges
    builder.add_edge(START, "intent_detection")

    builder.add_conditional_edges(
        "intent_detection",
        route_by_intent,
        {
            "simple_qa": "simple_qa",
            "planner": "planner",
        },
    )

    builder.add_edge("planner", "retriever")
    builder.add_edge("retriever", "ranker")
    builder.add_edge("ranker", "evaluator")

    builder.add_conditional_edges(
        "evaluator",
        route_after_evaluation,
        {
            "generator": "generator",
            "query_rewriter": "query_rewriter",
        },
    )

    builder.add_edge("query_rewriter", "retriever")
    builder.add_edge("simple_qa", END)
    builder.add_edge("generator", END)

    # Instantiate MemorySaver Checkpointer
    memory = MemorySaver()

    # Compile with checkpointer enabled
    return builder.compile(checkpointer=memory)


rag_app = build_graph()