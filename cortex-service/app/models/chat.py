"""Request and response models for chat operations."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat request payload."""

    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    """Outgoing chat response payload."""

    response: str

