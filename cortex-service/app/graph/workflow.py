from langgraph.graph import StateGraph, END, START
from app.graph.state import AgentState
from app.graph.nodes import (
    intent_detection_node,
    planner_node,
    retriever_node,
    ranker_node,
    generator_node,
    simple_qa_node,
)


def route_by_intent(state: AgentState) -> str:
    """Routes based on intent classification."""
    intent = state.get("intent", "retrieval_needed")
    if intent == "simple_qa":
        return "simple_qa"
    return "planner"


def build_graph():
    builder = StateGraph(AgentState)

    # Add Nodes
    builder.add_node("intent_detection", intent_detection_node)
    builder.add_node("simple_qa", simple_qa_node)
    builder.add_node("planner", planner_node)
    builder.add_node("retriever", retriever_node)
    builder.add_node("ranker", ranker_node)
    builder.add_node("generator", generator_node)

    # Add Edges
    builder.add_edge(START, "intent_detection")

    # Conditional Routing from Intent Detection
    builder.add_conditional_edges(
        "intent_detection",
        route_by_intent,
        {
            "simple_qa": "simple_qa",
            "planner": "planner",
        },
    )

    # Retrieval Pipeline Linear Flow
    builder.add_edge("planner", "retriever")
    builder.add_edge("retriever", "ranker")
    builder.add_edge("ranker", "generator")  # Direct connection to Generator!

    # Terminate Flow
    builder.add_edge("simple_qa", END)
    builder.add_edge("generator", END)

    return builder.compile()


# Compiled LangGraph Application
rag_app = build_graph()