from __future__ import annotations

from typing import Any

from app.connectors.gmail.metadata_client import (
    GmailMetadataClient,
)

from app.tools.gmail.service import GmailService


class GmailConnector:
    """
    Gmail connector exposed to the AI Service.

    Currently implemented:

        SEARCH

    Future operations:

        FETCH
        COUNT
        AGGREGATE
        FILTER
        CLASSIFY
        EXTRACT
        SUMMARIZE
    """

    name = "gmail"

    def __init__(
        self,
        gmail_service: GmailService,
    ):
        self._gmail_service = gmail_service

        self._metadata = GmailMetadataClient(
            gmail_service
        )

    async def search(
        self,
        query: str = "",
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search Gmail and return metadata + snippet.

        IMPORTANT:

        This method does NOT fetch full email bodies.
        """

        # ---------------------------------------------
        # 1. Gmail search
        # ---------------------------------------------

        response = await self._metadata.list_message_refs(
            query=query,
            max_results=top_k,
        )

        message_refs = response.get(
            "messages",
            []
        )

        # ---------------------------------------------
        # 2. Fetch lightweight metadata
        # ---------------------------------------------

        results = []

        for message_ref in message_refs:

            record = (
                await self._metadata
                .get_message_metadata(
                    message_ref["id"]
                )
            )

            results.append(
                {
                    "id": record.id,

                    "thread_id": record.thread_id,

                    "from": record.headers.get(
                        "From"
                    ),

                    "to": record.headers.get(
                        "To"
                    ),

                    "subject": record.headers.get(
                        "Subject"
                    ),

                    "date": record.headers.get(
                        "Date"
                    ),

                    "snippet": record.snippet,

                    "labels": record.label_ids,

                    "depth": "SNIPPET",
                }
            )

        return results


def build_default_gmail_connector() -> GmailConnector:

    gmail_service = GmailService()

    return GmailConnector(
        gmail_service
    )