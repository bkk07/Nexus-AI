import operator
from typing import TypedDict, List, Dict, Any, Annotated, Optional


class SubTask(TypedDict):
    id: int
    description: str


class EvidenceItem(TypedDict):
    content: str
    source: str
    score: float


class AgentState(TypedDict, total=False):
    # 1. User Input
    question: str
    
    # 2. Planning
    intent: str                          # "simple_qa" or "retrieval_needed"
    subtasks: List[SubTask]              # Decomposed tasks from Planner Node
    
    # 3. Retrieval & Ranking
    raw_evidence: Annotated[List[EvidenceItem], operator.add] # Appends parallel retrieval results
    ranked_evidence: List[EvidenceItem]  # Deduplicated and re-ranked evidence
    
    # 4. Generation & Output
    generation: str                     # Final answer from Llama-3.3-70b
    citations: List[Dict[str, Any]]      # Citations mapped to source blocks
    
    # 5. Graph Loop Management
    retry_count: int                     # Prevents infinite re-planning loops
    errors: Annotated[List[str], operator.add] # Error log channel