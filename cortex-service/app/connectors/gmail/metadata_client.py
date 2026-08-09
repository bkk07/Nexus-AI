from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.tools.gmail.service import GmailService


GMAIL_METADATA_HEADERS = [
    "From",
    "To",
    "Subject",
    "Date",
]


@dataclass(frozen=True)
class GmailMetadataRecord:
    """
    Lightweight Gmail message representation.

    Contains:
        - message ID
        - thread ID
        - selected headers
        - labels
        - snippet

    Does NOT fetch the full email body.
    """

    id: str

    thread_id: str | None = None

    headers: dict[str, str] = field(
        default_factory=dict
    )

    label_ids: list[str] = field(
        default_factory=list
    )

    snippet: str = ""


class GmailMetadataClient:

    def __init__(
        self,
        gmail_service: GmailService,
    ):
        self._gmail_service = gmail_service

    async def list_message_refs(
        self,
        query: str = "",
        max_results: int = 10,
        page_token: str | None = None,
    ) -> dict:

        def _request():

            request = (
                self._gmail_service.service
                .users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=max_results,
                    pageToken=page_token,
                )
            )

            return request.execute()

        return await asyncio.to_thread(
            _request
        )

    async def get_message_metadata(
        self,
        message_id: str,
    ) -> GmailMetadataRecord:

        def _request():

            request = (
                self._gmail_service.service
                .users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="metadata",
                    metadataHeaders=GMAIL_METADATA_HEADERS,
                )
            )

            return request.execute()

        message = await asyncio.to_thread(
            _request
        )

        payload = message.get(
            "payload",
            {}
        )

        headers = {
            header["name"]: header.get(
                "value",
                ""
            )
            for header in payload.get(
                "headers",
                []
            )
            if "name" in header
        }

        return GmailMetadataRecord(
            id=message["id"],
            thread_id=message.get(
                "threadId"
            ),
            headers=headers,
            label_ids=message.get(
                "labelIds",
                []
            ),
            snippet=message.get(
                "snippet",
                ""
            ),
        )