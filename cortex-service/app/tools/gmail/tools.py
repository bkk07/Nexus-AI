"""LangChain Tool Wrappers for Gmail API."""

from typing import Any, Dict, Optional
from langchain_core.tools import tool

from app.tools.gmail.schemas import ReadEmailInput, SearchEmailsInput
from app.tools.gmail.service import GmailService


@tool("gmail_search_emails", args_schema=SearchEmailsInput)
def gmail_search_emails(
    query: Optional[str] = None,
    unread_only: bool = False,
    starred_only: bool = False,
    has_attachment: bool = False,
    sender: Optional[str] = None,
    max_results: int = 10,
) -> Dict[str, Any]:
    """Search emails using queries (e.g., 'interview', 'offer letter', 'Google') or status filters (unread, starred)."""
    service = GmailService()
    messages = service.search_messages(
        query=query,
        unread_only=unread_only,
        starred_only=starred_only,
        has_attachment=has_attachment,
        sender=sender,
        max_results=max_results,
    )

    return {
        "count": len(messages),
        "emails": [msg.model_dump() for msg in messages],
    }


@tool("gmail_read_email", args_schema=ReadEmailInput)
def gmail_read_email(
    email_id: str,
) -> Dict[str, Any]:
    """Read full email body and details by email message ID."""
    service = GmailService()
    message = service.get_message_by_id(email_id)

    if not message:
        return {"error": f"Email with ID '{email_id}' could not be found."}

    return {"email": message.model_dump()}