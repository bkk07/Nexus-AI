from __future__ import annotations

import asyncio

from app.tools.gmail.service import GmailService


class GmailContentClient:
    """
    Full-content Gmail client.

    Used by FETCH.

    Unlike GmailMetadataClient, this client is allowed
    to retrieve the complete email payload.
    """

    def __init__(
        self,
        gmail_service: GmailService,
    ):
        self._gmail_service = gmail_service

    async def get_message(
        self,
        message_id: str,
    ) -> dict:

        def _request():

            request = (
                self._gmail_service.service
                .users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="full",
                )
            )

            return request.execute()

        return await asyncio.to_thread(
            _request
        )