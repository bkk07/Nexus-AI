"""Gmail API Service Wrapper using .env credentials."""

import base64
import logging
import os
from typing import Any, Dict, List, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from dotenv import load_dotenv
load_dotenv()
from app.tools.gmail.schemas import EmailMessage

logger = logging.getLogger(__name__)


class GmailService:
    """Wrapper around Google Gmail API v1 loading credentials directly from environment variables."""

    def __init__(self):
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")

        if not all([client_id, client_secret, refresh_token]):
            raise ValueError(
                "Missing Google OAuth environment variables. Ensure GOOGLE_CLIENT_ID, "
                "GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN are set in your .env file."
            )

        credentials = Credentials(
            token=None,  # Google client auto-refreshes using refresh_token
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        self.service: Resource = build("gmail", "v1", credentials=credentials)

    def search_messages(
        self,
        query: Optional[str] = None,
        unread_only: bool = False,
        starred_only: bool = False,
        has_attachment: bool = False,
        sender: Optional[str] = None,
        max_results: int = 10,
    ) -> List[EmailMessage]:
        """Search Gmail messages with filters and return detailed EmailMessage objects."""
        q_parts = []
        if query:
            q_parts.append(query)
        if unread_only:
            q_parts.append("is:unread")
        if starred_only:
            q_parts.append("is:starred")
        if has_attachment:
            q_parts.append("has:attachment")
        if sender:
            q_parts.append(f"from:{sender}")

        q_str = " ".join(q_parts)

        try:
            response = (
                self.service.users()
                .messages()
                .list(userId="me", q=q_str, maxResults=max_results)
                .execute()
            )

            messages = response.get("messages", [])
            results: List[EmailMessage] = []

            for msg_meta in messages:
                full_msg = self.get_message_by_id(msg_meta["id"])
                if full_msg:
                    results.append(full_msg)

            return results

        except Exception as e:
            logger.error(f"Error searching Gmail messages: {e}")
            return []

    def get_message_by_id(self, email_id: str) -> Optional[EmailMessage]:
        """Fetch and parse a single Gmail message by ID."""
        try:
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=email_id, format="full")
                .execute()
            )

            payload = msg.get("payload", {})
            headers = payload.get("headers", [])

            header_map = {
                h["name"].lower(): h["value"] for h in headers if "name" in h
            }

            labels = msg.get("labelIds", [])
            is_unread = "UNREAD" in labels
            is_starred = "STARRED" in labels

            body_text = self._extract_body(payload)
            attachment_names = self._extract_attachment_names(payload)

            return EmailMessage(
                id=msg["id"],
                thread_id=msg["threadId"],
                subject=header_map.get("subject", "(No Subject)"),
                sender=header_map.get("from", ""),
                recipient=header_map.get("to", ""),
                date=header_map.get("date", ""),
                snippet=msg.get("snippet", ""),
                body=body_text or msg.get("snippet", ""),
                is_unread=is_unread,
                is_starred=is_starred,
                has_attachments=len(attachment_names) > 0,
                attachment_names=attachment_names,
            )

        except Exception as e:
            logger.error(f"Error reading message ID {email_id}: {e}")
            return None

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Recursively decode plain text content from MIME structures."""
        mime_type = payload.get("mimeType", "")

        if mime_type == "text/plain" and "data" in payload.get("body", {}):
            return base64.urlsafe_b64decode(
                payload["body"]["data"].encode("UTF-8")
            ).decode("utf-8")

        parts = payload.get("parts", [])
        for part in parts:
            part_mime = part.get("mimeType", "")
            if part_mime == "text/plain" and "data" in part.get("body", {}):
                return base64.urlsafe_b64decode(
                    part["body"]["data"].encode("UTF-8")
                ).decode("utf-8")
            elif "parts" in part:
                sub_body = self._extract_body(part)
                if sub_body:
                    return sub_body

        return ""

    def _extract_attachment_names(self, payload: Dict[str, Any]) -> List[str]:
        """Extract attachment filenames from MIME payload."""
        names = []
        parts = payload.get("parts", [])
        for part in parts:
            filename = part.get("filename")
            if filename and part.get("body", {}).get("attachmentId"):
                names.append(filename)
        return names