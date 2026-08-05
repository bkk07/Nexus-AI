"""Pydantic schemas for Gmail Tools."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EmailMessage(BaseModel):
    """Structured representation of an email message."""

    id: str = Field(..., description="Gmail message ID")
    thread_id: str = Field(..., description="Gmail thread ID")
    subject: str = Field(default="", description="Email subject line")
    sender: str = Field(default="", description="From address/name")
    recipient: str = Field(default="", description="To address")
    date: str = Field(default="", description="Date sent/received")
    snippet: str = Field(default="", description="Short text snippet")
    body: str = Field(default="", description="Full email plain-text body")
    is_unread: bool = Field(default=False, description="Unread status flag")
    is_starred: bool = Field(default=False, description="Starred status flag")
    has_attachments: bool = Field(
        default=False, description="Attachment presence flag"
    )
    attachment_names: List[str] = Field(
        default_factory=list, description="List of attachment file names"
    )


class SearchEmailsInput(BaseModel):
    """Input parameters for searching emails."""

    query: Optional[str] = Field(
        default=None,
        description="Search query or terms (e.g., 'interview', 'offer letter', 'Google')",
    )
    unread_only: bool = Field(
        default=False, description="Filter for unread messages only"
    )
    starred_only: bool = Field(
        default=False, description="Filter for starred messages only"
    )
    has_attachment: bool = Field(
        default=False, description="Filter for emails with attachments"
    )
    sender: Optional[str] = Field(
        default=None, description="Filter by sender email address or name"
    )
    max_results: int = Field(
        default=10, description="Maximum number of emails to retrieve (1-50)"
    )


class ReadEmailInput(BaseModel):
    """Input parameters for fetching a specific email by ID."""

    email_id: str = Field(
        ..., description="The unique Gmail message ID to fetch"
    )