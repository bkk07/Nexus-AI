from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage

from app.graph.state import AgentState
from app.llm.groq_client import get_reasoning_llm


logger = logging.getLogger(__name__)


def generator_node(
    state: AgentState,
) -> dict[str, Any]:
    """
    Generates the final response.

    Supports:

    1. New operation_results
    2. Existing ranked_evidence
    """

    question = state.get(
        "question",
        "",
    )

    operation_results = state.get(
        "operation_results",
        {},
    )

    ranked_evidence = state.get(
        "ranked_evidence",
        [],
    )

    llm = get_reasoning_llm()

    logger.info(
        "[GENERATOR] question=%s operation_result_keys=%s ranked_evidence_count=%s generation_context_type=%s",
        question,
        list(operation_results.keys()),
        len(ranked_evidence),
        "both"
        if operation_results and ranked_evidence
        else "operation"
        if operation_results
        else "evidence"
        if ranked_evidence
        else "none",
    )

    operation_context = ""

    if operation_results:
        context_blocks = []

        for operation_name, result in operation_results.items():
            if (
                isinstance(result, dict)
                and result.get("status")
                in {
                    "PENDING_LLM",
                    "UNSUPPORTED_OPERATION",
                    "UNSUPPORTED_CONNECTOR",
                }
            ):
                continue

            context_blocks.append(
                f"Operation: {operation_name}\n"
                f"Result: {result}"
            )

        if context_blocks:
            operation_context = "\n\n".join(context_blocks)

    evidence_context = ""

    if ranked_evidence:
        context_blocks = []

        for idx, item in enumerate(ranked_evidence, start=1):
            source = item.get("source", "Unknown")
            content = item.get("content", "")

            context_blocks.append(
                f"[{idx}] "
                f"(Source: {source})\n"
                f"{content}"
            )

        evidence_context = "\n\n".join(context_blocks)

    if not operation_context and not evidence_context:
        formatted_context = "No specific retrieved context available."
    elif operation_context and evidence_context:
        formatted_context = (
            "OPERATION RESULTS:\n"
            f"{operation_context}\n\n"
            "RETRIEVED EVIDENCE:\n"
            f"{evidence_context}"
        )
    elif operation_context:
        formatted_context = (
            "OPERATION RESULTS:\n"
            f"{operation_context}"
        )
    else:
        formatted_context = (
            "RETRIEVED EVIDENCE:\n"
            f"{evidence_context}"
        )

    today = datetime.now().strftime("%A, %B %d, %Y")

    system_prompt = f"""
You are an enterprise AI assistant.
Today's date is {today}.

Answer the user's question using the supplied
operation results and retrieved evidence.

Rules:

1. Use operation results when they directly
   answer the user's question.

2. Use retrieved evidence when answering
   questions based on emails or documents.

3. Never expose internal implementation details
   such as operation names, connectors,
   execution plans, or internal statuses.

4. If the user asks for a count, give the
   count clearly and concisely.

5. If the user asks for a summary, summarize
   the supplied content concisely.

6. Do not invent information that is not present
   in the supplied context.

7. For evidence-based answers, citations may be
   included using [1], [2], etc.

Context:
-----------------------
{formatted_context}
-----------------------

Question:
{question}

Final Answer:
"""

    logger.info("[GENERATOR] invoking_llm=true")

    response = llm.invoke(system_prompt)

    answer_text = response.content

    PREVIEW_LENGTH = 350
    citations = []

    for idx, item in enumerate(ranked_evidence):
        full_content = item.get("content", "")
        snippet = full_content[:PREVIEW_LENGTH].strip()

        if len(full_content) > PREVIEW_LENGTH:
            snippet += "..."

        citations.append(
            {
                "index": idx + 1,
                "source": item.get("source", "Unknown"),
                "snippet": snippet,
            }
        )

    logger.info(
        "[GENERATOR] answer_generated=true answer_length=%s",
        len(answer_text) if isinstance(answer_text, str) else 0,
    )

    return {
        "generation": answer_text,
        "citations": citations,
        "messages": [AIMessage(content=answer_text)],
    }