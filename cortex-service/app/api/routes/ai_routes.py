import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field, field_validator

from app.graph.workflow import rag_app


class AiAnswerRequest(BaseModel):
    question: str = Field(..., min_length=1)
    project_id: str
    conversation_id: Optional[str] = None
    conversation_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("question must be non-empty")
        return cleaned


class AiAnswerResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    task_trace: List[Dict[str, Any]] = Field(default_factory=list)
    latency_ms: float


ai_router = APIRouter(prefix="/ai", tags=["internal-ai"])


def _build_task_trace(tasks: Any) -> List[Dict[str, Any]]:
    trace: List[Dict[str, Any]] = []
    if not isinstance(tasks, list):
        return trace

    for task in tasks:
        if isinstance(task, dict):
            subtask = task.get("subtask")
            tool_name = task.get("tool_name") or task.get("tool")
        else:
            subtask_obj = getattr(task, "subtask", None)
            if subtask_obj is not None:
                subtask = getattr(subtask_obj, "description", None) or str(subtask_obj)
            else:
                subtask = getattr(task, "description", None) or str(task)
            tool_name = getattr(task, "tool_name", None) or getattr(task, "tool", None)

        trace.append(
            {
                "subtask": subtask or "",
                "tool": tool_name or "",
            }
        )

    return trace


@ai_router.post("/answer", response_model=AiAnswerResponse)
async def answer_question(request: AiAnswerRequest) -> AiAnswerResponse:
    start = time.perf_counter()

    try:
        thread_id = request.conversation_id or str(uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        inputs = {
            "question": request.question,
            "project_id": request.project_id,
            "messages": [HumanMessage(content=request.question)],
        }

        result = await rag_app.ainvoke(inputs, config=config)

        answer = result.get("generation") or result.get("answer", "")
        citations = result.get("citations", [])
        routed_or_subtasks = result.get("routed_tasks") or result.get("subtasks", [])
        task_trace = _build_task_trace(routed_or_subtasks)

        latency_ms = (time.perf_counter() - start) * 1000.0

        return AiAnswerResponse(
            answer=answer,
            citations=citations if isinstance(citations, list) else [],
            task_trace=task_trace,
            latency_ms=latency_ms,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal Server Error") from exc
