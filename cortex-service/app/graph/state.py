from typing import TypedDict, List, Optional, Dict, Any, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class SubTask(TypedDict):
    id: int
    description: str


class EvidenceItem(TypedDict, total=False):
    content: str
    source: str
    score: float
    normalized_score: float
    source_type: Optional[str]
    source_ref_id: Optional[str]
    metadata: Optional[Dict[str, Any]]


class AgentState(TypedDict, total=False):
    # Multi-tenant Scope
    project_id: str

    # Conversation Memory
    messages: Annotated[List[BaseMessage], add_messages]

    # Workflow Attributes
    question: str
    intent: Optional[str]
    subtasks: Optional[List[SubTask]]
    routed_tasks: Optional[List[Dict[str, Any]]]
    raw_evidence: Optional[List[EvidenceItem]]
    collected_evidence: Optional[List[EvidenceItem]]
    ranked_evidence: Optional[List[EvidenceItem]]
    generation: Optional[str]
    citations: Optional[List[dict]]
    is_relevant: Optional[bool]
    retry_count: Optional[int]