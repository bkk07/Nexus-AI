"""LangChain Tool Wrappers for Gmail API with AI Intelligence."""

from typing import Any, Dict, Optional
from langchain_core.tools import tool
from langchain_groq import ChatGroq

from app.tools.gmail.schemas import ReadEmailInput, SearchEmailsInput
from app.tools.gmail.service import GmailService

# Shared LLM instance for on-the-fly email intelligence
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)


@tool("gmail_search_emails", args_schema=SearchEmailsInput)
def gmail_search_emails(
    query: Optional[str] = None,
    unread_only: bool = False,
    starred_only: bool = False,
    has_attachment: bool = False,
    sender: Optional[str] = None,
    max_results: int = 10,
) -> Dict[str, Any]:
    """Search emails using queries (e.g. 'interview', 'invoice') or filters (unread, starred)."""
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
    """Read full email body and metadata by message ID."""
    service = GmailService()
    message = service.get_message_by_id(email_id)

    if not message:
        return {"error": f"Email with ID '{email_id}' could not be found."}

    return {"email": message.model_dump()}


@tool("gmail_summarize_emails")
def gmail_summarize_emails(
    query: Optional[str] = None,
    max_results: int = 5,
) -> Dict[str, Any]:
    """Search recent emails and generate a concise AI summary of key updates and threads."""
    service = GmailService()
    messages = service.search_messages(query=query, max_results=max_results)

    if not messages:
        return {"summary": "No relevant emails found to summarize."}

    formatted_texts = [
        f"From: {msg.sender}\nSubject: {msg.subject}\nDate: {msg.date}\nContent: {msg.body[:500]}"
        for msg in messages
    ]
    prompt = (
        "Summarize the following email messages concisely into bullet points. "
        "Highlight key updates, senders, and urgent matters:\n\n"
        + "\n---\n".join(formatted_texts)
    )

    response = llm.invoke(prompt)
    return {
        "count": len(messages),
        "summary": response.content,
    }


@tool("gmail_extract_action_items")
def gmail_extract_action_items(
    max_results: int = 10,
) -> Dict[str, Any]:
    """Extract pending action items, dates, meeting requests, and deadlines from recent unread/starred emails."""
    service = GmailService()
    messages = service.search_messages(unread_only=True, max_results=max_results)

    if not messages:
        messages = service.search_messages(max_results=max_results)

    if not messages:
        return {"action_items": []}

    formatted_texts = [
        f"ID: {msg.id} | From: {msg.sender} | Subject: {msg.subject}\nBody Snippet: {msg.body[:400]}"
        for msg in messages
    ]
    prompt = (
        "Extract actionable tasks, requested deadlines, and follow-ups from these emails. "
        "List each item with its Sender, Task Description, and Priority (High/Medium/Low):\n\n"
        + "\n---\n".join(formatted_texts)
    )

    response = llm.invoke(prompt)
    return {
        "processed_emails": len(messages),
        "action_items_summary": response.content,
    }


@tool("gmail_inbox_analytics")
def gmail_inbox_analytics() -> Dict[str, Any]:
    """Generate high-level stats about recent emails (unread counts, frequent senders, attachment frequency)."""
    service = GmailService()
    recent_emails = service.search_messages(max_results=20)

    if not recent_emails:
        return {"message": "No emails found for analysis."}

    unread_count = sum(1 for m in recent_emails if m.is_unread)
    attachment_count = sum(1 for m in recent_emails if m.has_attachments)

    senders: Dict[str, int] = {}
    for msg in recent_emails:
        sender_clean = msg.sender.split("<")[-1].replace(">", "").strip()
        senders[sender_clean] = senders.get(sender_clean, 0) + 1

    top_senders = sorted(senders.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "sample_size": len(recent_emails),
        "unread_in_sample": unread_count,
        "emails_with_attachments": attachment_count,
        "top_senders": [{"sender": s, "count": c} for s, c in top_senders],
    }