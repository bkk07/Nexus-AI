"""Shared Pydantic schemas for the Gmail integration tool."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    content: str
    source: str
    score: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )


class EmailMessage(BaseModel):
    id: str
    thread_id: str

    subject: str = "(No Subject)"
    sender: str = ""
    recipient: str = ""
    date: str = ""

    snippet: str = ""
    body: str = ""

    is_unread: bool = False
    is_starred: bool = False

    has_attachments: bool = False
    attachment_names: List[str] = Field(
        default_factory=list
    )


class GmailActionType(str, Enum):
    SEARCH_EMAILS = "search_emails"
    GET_THREAD = "get_thread"
    GET_UNREAD_SUMMARY = "get_unread_summary"
    CREATE_DRAFT = "create_draft"


class GmailToolArgs(BaseModel):
    action: GmailActionType = Field(
        default=GmailActionType.SEARCH_EMAILS
    )

    query: Optional[str] = None
    thread_id: Optional[str] = None

    to: Optional[List[str]] = None
    subject: Optional[str] = None
    body: Optional[str] = None

    max_results: int = Field(
        default=10,
        le=50
    )


class DraftResult(BaseModel):
    draft_id: str
    thread_id: Optional[str]
    created_at: datetime