from __future__ import annotations

from typing import Any, List

from app.graph.state import AgentState, EvidenceItem


def collector_node(
    state: AgentState,
) -> dict[str, Any]:
    """
    Flattens raw evidence and normalizes raw scores
    to a standardized 0.0 - 1.0 range.
    """

    print("\n--- [NODE] Evidence Collector ---")

    raw_evidence = state.get(
        "raw_evidence"
    ) or []

    if not raw_evidence:
        print(
            " -> No raw evidence collected."
        )

        return {
            "collected_evidence": []
        }

    scores = [
        float(
            item.get(
                "score",
                0.0,
            )
        )
        for item in raw_evidence
    ]

    max_score = (
        max(scores)
        if scores
        else 1.0
    )

    min_score = (
        min(scores)
        if scores
        else 0.0
    )

    score_range = (
        max_score - min_score
    )

    collected_evidence: List[
        EvidenceItem
    ] = []

    for item in raw_evidence:

        raw_score = float(
            item.get(
                "score",
                0.0,
            )
        )

        if score_range > 0:

            norm_score = (
                raw_score - min_score
            ) / score_range

        else:

            norm_score = 0.8

        normalized_item = {
            **item,
            "normalized_score": round(
                norm_score,
                4,
            ),
        }

        collected_evidence.append(
            normalized_item
        )

    print(
        " -> Collected and normalized "
        f"{len(collected_evidence)} "
        "evidence items."
    )

    return {
        "collected_evidence":
            collected_evidence
    }