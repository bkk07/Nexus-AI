from __future__ import annotations

import json
from typing import Any

from app.graph.state import AgentState
from app.llm.groq_client import get_fast_llm


def evaluator_node(
    state: AgentState,
) -> dict[str, Any]:
    """
    Grades whether retrieved evidence is sufficient
    to answer the question.
    """

    print(
        "\n--- [NODE] Relevance Evaluator ---"
    )

    question = state.get(
        "question",
        "",
    )

    ranked_evidence = state.get(
        "ranked_evidence",
        [],
    )

    retry_count = state.get(
        "retry_count"
    ) or 0

    # ----------------------------------------------------------
    # No evidence
    # ----------------------------------------------------------

    if not ranked_evidence:

        print(
            " -> No evidence retrieved. "
            "Grading as 'no'."
        )

        return {
            "is_relevant": False,
            "retry_count": retry_count + 1,
        }

    # ----------------------------------------------------------
    # Evaluate evidence
    # ----------------------------------------------------------

    try:

        llm = get_fast_llm().bind(
            response_format={
                "type": "json_object"
            }
        )

        context_sample = "\n---\n".join(
            [
                item.get(
                    "content",
                    "",
                )[:300]
                for item in ranked_evidence[:3]
            ]
        )

        prompt = (
            "You are an evidence relevance evaluator.\n"
            "Evaluate whether the retrieved documents "
            "contain information relevant to fulfilling "
            "the user request.\n\n"

            "IMPORTANT EVALUATION RULES:\n"

            "1. For open-ended or summary requests "
            "(e.g., 'summarize emails', 'check my inbox', "
            "'latest messages'), grade 'YES' as long as "
            "the retrieved documents are emails/messages "
            "from the requested timeframe or source.\n"

            "2. Grade 'NO' ONLY if the retrieved documents "
            "are completely off-topic or empty.\n\n"

            f"User Question: {question}\n\n"

            f"Retrieved Context Sample:\n"
            f"{context_sample}\n\n"

            'Respond ONLY with a JSON object: '
            '{"binary_score": "yes"} or '
            '{"binary_score": "no"}'
        )

        response = llm.invoke(
            prompt
        )

        data = json.loads(
            response.content
        )

        binary_score = (
            data.get(
                "binary_score",
                "yes",
            )
            .lower()
            .strip()
        )

        is_relevant = (
            binary_score == "yes"
        )

        print(
            f" -> Evidence Grade: "
            f"'{binary_score.upper()}' "
            f"| Relevancy: {is_relevant}"
        )

    except Exception as e:

        print(
            " -> [!] Evaluator parsing issue "
            f"({e}). Defaulting relevancy "
            "to True to continue flow."
        )

        is_relevant = True

    return {
        "is_relevant": is_relevant,
        "retry_count": retry_count + 1,
    }