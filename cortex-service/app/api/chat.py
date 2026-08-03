"""Chat router for Stage 2 LLM access."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_llm
from app.llm.base import LLMAuthenticationError, LLMNetworkError, LLMProvider, LLMProviderError, LLMServiceError
from app.models.chat import ChatRequest, ChatResponse


router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, llm: LLMProvider = Depends(get_llm)) -> ChatResponse:
    """Forward a validated prompt to the configured LLM provider."""

    try:
        response_text = await llm.chat(request.message)
    except LLMAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except LLMNetworkError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return ChatResponse(response=response_text)
