from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.tools.gmail.service import GmailService


logger = logging.getLogger(__name__)


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

        logger.debug(
            "[GMAIL_CONTENT] fetching_message_id=%s",
            message_id,
        )

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

        message = await asyncio.to_thread(_request)

        logger.debug(
            "[GMAIL_CONTENT] message_id=%s payload_present=%s",
            message.get("id", message_id),
            message.get("payload") is not None,
        )

        return message