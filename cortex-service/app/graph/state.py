from typing import TypedDict, List, Optional, Dict, Any, Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from app.core.execution_plan import ExecutionPlan

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
    # ============================================================
    # Multi-tenant Scope
    # ============================================================

    project_id: str

    # ============================================================
    # Conversation Memory
    # ============================================================

    messages: Annotated[
        List[BaseMessage],
        add_messages,
    ]

    # ============================================================
    # Workflow Attributes
    # ============================================================

    question: str
    intent: Optional[str]

    subtasks: Optional[
        List[SubTask]
    ]

    routed_tasks: Optional[
        List[Dict[str, Any]]
    ]

    # ============================================================
    # Operation Planning
    #
    # What the Agent has decided to execute.
    #
    # Example:
    #
    # {
    #     "operations": [
    #         {
    #             "type": "SEARCH",
    #             "connector": "gmail"
    #         },
    #         {
    #             "type": "FETCH",
    #             "connector": "gmail"
    #         },
    #         {
    #             "type": "SUMMARIZE",
    #             "connector": "gmail"
    #         }
    #     ]
    # }
    # ============================================================

    operation_plan: Optional[ExecutionPlan]

    # ============================================================
    # Operation Results
    #
    # Stores the output produced by operations.
    #
    # Example:
    #
    # {
    #     "search": {...},
    #     "fetch": {...},
    #     "count": {...},
    #     "filter": {...},
    #     "classify": {...},
    #     "extract": {...},
    #     "summarize": {...}
    # }
    # ============================================================

    operation_results: Optional[
        Dict[str, Any]
    ]

    # ============================================================
    # Evidence Pipeline
    # ============================================================

    raw_evidence: Optional[
        List[EvidenceItem]
    ]

    collected_evidence: Optional[
        List[EvidenceItem]
    ]

    ranked_evidence: Optional[
        List[EvidenceItem]
    ]

    # ============================================================
    # Final Generation
    # ============================================================

    generation: Optional[str]

    citations: Optional[
        List[dict]
    ]

    is_relevant: Optional[bool]

    retry_count: Optional[int]