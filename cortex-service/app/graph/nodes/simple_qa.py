from __future__ import annotations

from typing import Any

from langchain_core.messages import (
    SystemMessage,
    AIMessage,
)

from app.llm.groq_client import get_fast_llm
from app.graph.state import AgentState


def simple_qa_node(
    state: AgentState,
) -> dict[str, Any]:
    """
    Handles conversational turns and simple QA
    using the current conversation messages.
    """

    print("\n--- [NODE] Simple QA ---")

    messages = state.get(
        "messages",
        [],
    )

    system_prompt = SystemMessage(
        content=(
            "You are a polite, helpful enterprise "
            "AI assistant. Respond concisely and "
            "utilize the previous conversation "
            "history when answering."
        )
    )

    prompt_messages = [
        system_prompt,
        *messages,
    ]

    llm = get_fast_llm()

    response = llm.invoke(
        prompt_messages
    )

    answer_text = response.content

    return {
        "generation": answer_text,
        "citations": [],
        "messages": [
            AIMessage(
                content=answer_text
            )
        ],
    }