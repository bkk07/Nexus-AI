from __future__ import annotations

import asyncio
from typing import Any

from app.tools.gmail.service import GmailService


class GmailContentClient:
    """
    Gmail full-content API client.

    Responsible only for retrieving the raw
    full Gmail message.
    """

    def __init__(
        self,
        gmail_service: GmailService,
    ):
        self._gmail_service = gmail_service

    async def get_message(
        self,
        message_id: str,
    ) -> dict[str, Any]:

        def _request():
            return (
                self._gmail_service.service
                .users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="full",
                )
                .execute()
            )

        return await asyncio.to_thread(_request)