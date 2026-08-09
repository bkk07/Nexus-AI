from __future__ import annotations

from typing import Any, List

from app.graph.state import AgentState, EvidenceItem


def ranker_node(
    state: AgentState,
) -> dict[str, Any]:
    """
    Deduplicates and ranks normalized evidence chunks.
    """

    print("\n--- [NODE] Evidence Ranker ---")

    evidence_pool = (
        state.get("collected_evidence")
        or state.get("raw_evidence")
        or []
    )

    seen_contents = set()

    deduped_evidence: List[
        EvidenceItem
    ] = []

    for item in evidence_pool:

        content = item.get(
            "content",
            "",
        )

        if (
            content
            and content not in seen_contents
        ):
            seen_contents.add(content)

            deduped_evidence.append(
                item
            )

    sorted_evidence = sorted(
        deduped_evidence,
        key=lambda x: x.get(
            "normalized_score",
            x.get("score", 0.0),
        ),
        reverse=True,
    )

    top_ranked = sorted_evidence[:8]

    print(
        " -> Deduplicated from "
        f"{len(evidence_pool)} "
        f"to {len(deduped_evidence)} items."
    )

    print(
        " -> Retained top "
        f"{len(top_ranked)} ranked chunk(s)."
    )

    return {
        "ranked_evidence": top_ranked,
    }