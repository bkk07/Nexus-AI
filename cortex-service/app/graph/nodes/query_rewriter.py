from __future__ import annotations

from typing import Any, List

from app.graph.state import AgentState, SubTask
from app.llm.groq_client import get_fast_llm


def query_rewriter_node(
    state: AgentState,
) -> dict[str, Any]:
    """
    Reformulates the query for a secondary search attempt.
    """

    print(
        "\n--- [NODE] Query Rewriter ---"
    )

    question = state.get(
        "question",
        "",
    )

    retry_count = state.get(
        "retry_count",
        1,
    )

    llm = get_fast_llm()

    prompt = (
        "The initial search for the user request failed:\n"
        f"Request: '{question}'\n\n"
        "Generate a 2-4 word keyword query optimized "
        "for email search (e.g., 'recent emails', "
        "'inbox updates').\n"
        "DO NOT write long sentences, lists of dates, "
        "or month names. Output ONLY the short query."
    )

    response = llm.invoke(
        prompt
    )

    rewritten_query = (
        response.content
        .strip()
        .replace('"', '')
    )

    print(
        f" -> Rewrote Query "
        f"(Attempt #{retry_count}): "
        f"'{rewritten_query}'"
    )

    new_subtasks: List[SubTask] = [
        {
            "id": 1,
            "description": rewritten_query,
        }
    ]

    return {
        "subtasks": new_subtasks,
    }