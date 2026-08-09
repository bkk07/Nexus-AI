from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.llm.groq_client import get_fast_llm
from app.graph.state import AgentState


class IntentClassification(BaseModel):
    intent: Literal[
        "simple_qa",
        "retrieval_needed",
    ] = Field(
        description=(
            "MUST be either 'simple_qa' or "
            "'retrieval_needed'.\n"
            "- Use 'retrieval_needed' whenever "
            "the user asks to search, check, find, "
            "or retrieve information from external "
            "sources like emails, inbox, documents, "
            "policies, notion notes, or calendar "
            "schedules.\n"
            "- Use 'simple_qa' ONLY for greetings, "
            "chitchat, general knowledge, introducing "
            "oneself, or meta-questions about the "
            "ongoing conversation history."
        )
    )


def intent_detection_node(
    state: AgentState,
) -> dict:
    """
    Classifies the user query to determine whether
    external data retrieval is required.
    """

    print(
        "\n--- [NODE] Intent Detection ---"
    )

    question = state.get(
        "question",
        "",
    )

    llm = get_fast_llm()

    structured_llm = (
        llm.with_structured_output(
            IntentClassification
        )
    )

    prompt = (
        "Analyze the following user query "
        "and classify its intent:\n\n"
        f"Query: {question}"
    )

    result: IntentClassification = (
        structured_llm.invoke(prompt)
    )

    print(
        f"-> Classified Intent: "
        f"'{result.intent}'"
    )

    return {
        "intent": result.intent,
    }