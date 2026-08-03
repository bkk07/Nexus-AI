from typing import TypedDict, List, Optional


class SubTask(TypedDict):
    id: int
    description: str


class EvidenceItem(TypedDict):
    content: str
    source: str
    score: float


class AgentState(TypedDict):
    question: str
    intent: Optional[str]
    subtasks: Optional[List[SubTask]]
    raw_evidence: Optional[List[EvidenceItem]]
    ranked_evidence: Optional[List[EvidenceItem]]
    generation: Optional[str]
    citations: Optional[List[dict]]
    # --- New Reflection State Fields ---
    is_relevant: Optional[bool]
    retry_count: Optional[int]