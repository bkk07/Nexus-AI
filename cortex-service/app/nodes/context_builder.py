"""Context Builder Node (SAD Chapter 8.15).

Assembles system instructions, numbered evidence blocks, conversation history,
and builds the citation lookup map for generation post-processing.
"""

from typing import Any, Dict
from app.graph.state import AgentState


def context_builder_node(state: AgentState) -> Dict[str, Any]:
    print("\n--- [NODE] Context Builder ---")

    ranked_evidence = state.get("ranked_evidence") or []
    question = state.get("question", "")
    history = state.get("conversation_history") or []

    citation_map: Dict[int, Any] = {}
    evidence_blocks = []

    # 1. Map ranked evidence items to discrete numeric indices
    for idx, item in enumerate(ranked_evidence, start=1):
        citation_map[idx] = item

        # Extract attributes whether item is a dict or Pydantic model
        if isinstance(item, dict):
            source_type = item.get("source_type", "unknown")
            source_ref_id = item.get("source_ref_id", "")
            content = item.get("content", "")
            metadata = item.get("metadata", {})
        else:
            source_type = getattr(item, "source_type", "unknown")
            source_ref_id = getattr(item, "source_ref_id", "")
            content = getattr(item, "content", "")
            metadata = getattr(item, "metadata", {})

        meta_info = (
            f" (Page {metadata.get('page_number')})"
            if "page_number" in metadata
            else ""
        )
        evidence_blocks.append(
            f"[{idx}] Source ({source_type}:{source_ref_id}){meta_info}:\n{content}"
        )

    formatted_evidence = (
        "\n\n".join(evidence_blocks)
        if evidence_blocks
        else "No external evidence available."
    )

    # 2. Build system instructions instructing the model to cite using [n] markers
    system_prompt = (
        "You are Cortex AI, an enterprise assistant.\n"
        "Answer the question based strictly on the provided evidence below.\n"
        "For every claim or factual assertion derived from the evidence, cite its source number in brackets, e.g., [1] or [2].\n"
        "Do NOT invent citations. If no relevant information is present in the evidence, state clearly that you cannot find the answer.\n\n"
        f"--- GROUNDED EVIDENCE ---\n{formatted_evidence}\n--- END EVIDENCE ---"
    )

    # 3. Construct message list ready for LLM consumption
    context_messages = [{"role": "system", "content": system_prompt}]

    # Append past conversation history if available
    for msg in history:
        if isinstance(msg, dict):
            context_messages.append(msg)

    # Append current user question
    context_messages.append({"role": "user", "content": question})

    print(
        f" -> Mapped {len(citation_map)} citation source(s) into context window."
    )

    return {
        "context_messages": context_messages,
        "citation_map": citation_map,
    }