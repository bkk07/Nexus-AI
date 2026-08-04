from typing import TypedDict, List, Optional, Dict, Any, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class SubTask(TypedDict):
    id: int
    description: str


class EvidenceItem(TypedDict):
    content: str
    source: str
    score: float


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
    ranked_evidence: Optional[List[EvidenceItem]]
    generation: Optional[str]
    citations: Optional[List[dict]]
    is_relevant: Optional[bool]
    retry_count: Optional[int]