from langgraph.graph import StateGraph, END, START
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
    """Routes based on intent classification."""
    intent = state.get("intent", "retrieval_needed")
    if intent == "simple_qa":
        return "simple_qa"
    return "planner"


def route_after_evaluation(state: AgentState) -> str:
    """Determines whether to generate answer or rewrite query based on evaluation."""
    is_relevant = state.get("is_relevant", False)
    retry_count = state.get("retry_count", 0)

    # Allow up to 2 retrieval attempts before forcing generator
    if is_relevant or retry_count >= 2:
        if not is_relevant:
            print("-> Max retries (2) reached. Proceeding to generator with available context.")
        return "generator"
    else:
        print("-> Context insufficient. Routing to Query Rewriter...")
        return "query_rewriter"


def build_graph():
    builder = StateGraph(AgentState)

    # Add All Nodes
    builder.add_node("intent_detection", intent_detection_node)
    builder.add_node("simple_qa", simple_qa_node)
    builder.add_node("planner", planner_node)
    builder.add_node("retriever", retriever_node)
    builder.add_node("ranker", ranker_node)
    builder.add_node("evaluator", evaluator_node)
    builder.add_node("query_rewriter", query_rewriter_node)
    builder.add_node("generator", generator_node)

    # Add Linear & Conditional Edges
    builder.add_edge(START, "intent_detection")

    builder.add_conditional_edges(
        "intent_detection",
        route_by_intent,
        {
            "simple_qa": "simple_qa",
            "planner": "planner",
        },
    )

    # Retrieval -> Ranker -> Evaluator pipeline
    builder.add_edge("planner", "retriever")
    builder.add_edge("retriever", "ranker")
    builder.add_edge("ranker", "evaluator")

    # Reflection Conditional Router
    builder.add_conditional_edges(
        "evaluator",
        route_after_evaluation,
        {
            "generator": "generator",
            "query_rewriter": "query_rewriter",
        },
    )

    # Loop Rewriter back into Retriever
    builder.add_edge("query_rewriter", "retriever")

    # Terminal Edges
    builder.add_edge("simple_qa", END)
    builder.add_edge("generator", END)

    return builder.compile()


rag_app = build_graph()