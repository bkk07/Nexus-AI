from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.graph.nodes import collector_node


from app.graph.state import AgentState
from app.graph.nodes import (
    intent_detection_node,
    planner_node,
    router_node,
    execute_tools_node,
    ranker_node,
    evaluator_node,
    query_rewriter_node,
    generator_node,
    simple_qa_node,
)


def route_by_intent(state: AgentState) -> str:
    """Routes based on initial query intent classification."""
    intent = state.get("intent", "simple_qa")
    if intent == "retrieval_needed":
        return "planner_node"
    return "simple_qa_node"


def route_after_evaluator(state: AgentState) -> str:
    """Evaluates evidence relevance and manages re-write retries."""
    is_relevant = state.get("is_relevant", False)
    retry_count = state.get("retry_count", 0)

    if is_relevant:
        return "generator_node"

    if retry_count < 2:
        return "query_rewriter_node"

    # Fall back to generator if retry limit reached
    return "generator_node"


# Build the Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("intent_detection_node", intent_detection_node)
workflow.add_node("simple_qa_node", simple_qa_node)
workflow.add_node("planner_node", planner_node)
workflow.add_node("router_node", router_node)
workflow.add_node("execute_tools_node", execute_tools_node)
workflow.add_node("ranker_node", ranker_node)
workflow.add_node("evaluator_node", evaluator_node)
workflow.add_node("query_rewriter_node", query_rewriter_node)
workflow.add_node("generator_node", generator_node)
workflow.add_node("collector_node", collector_node)


# Set Entry Point
workflow.add_edge(START, "intent_detection_node")

# Conditional Edge for Intent
workflow.add_conditional_edges(
    "intent_detection_node",
    route_by_intent,
    {
        "simple_qa_node": "simple_qa_node",
        "planner_node": "planner_node",
    },
)

# Retrieval Sub-Graph Chain
workflow.add_edge("planner_node", "router_node")
workflow.add_edge("router_node", "execute_tools_node")

workflow.add_edge("execute_tools_node", "collector_node")
workflow.add_edge("collector_node", "ranker_node")

workflow.add_edge("ranker_node", "evaluator_node")

# Conditional Edge after Evaluation (Reflection Loop)
workflow.add_conditional_edges(
    "evaluator_node",
    route_after_evaluator,
    {
        "generator_node": "generator_node",
        "query_rewriter_node": "query_rewriter_node",
    },
)


# Re-writer routes directly back to router for target tools
workflow.add_edge("query_rewriter_node", "router_node")

# Output Edges
workflow.add_edge("simple_qa_node", END)
workflow.add_edge("generator_node", END)



# In-Memory Checkpointer
checkpointer = MemorySaver()
rag_app = workflow.compile(checkpointer=checkpointer)