from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from app.tools.gmail.service import GmailService


GMAIL_METADATA_HEADERS = [
    "From",
    "To",
    "Subject",
    "Date",
]


logger = logging.getLogger(__name__)


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

        logger.debug(
            "[GMAIL_METADATA] list_message_refs query=%s max_results=%s page_token_present=%s",
            query,
            max_results,
            page_token is not None,
        )

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

        response = await asyncio.to_thread(
            _request
        )

        messages = response.get("messages", [])

        logger.debug(
            "[GMAIL_METADATA] returned_messages=%s next_page_token_present=%s result_size_estimate=%s",
            len(messages),
            response.get("nextPageToken") is not None,
            response.get("resultSizeEstimate"),
        )

        return response

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

    async def get_messages_metadata_batch(
        self,
        message_ids: list[str],
        headers: list[str] | None = None,
    ) -> tuple[dict[str, GmailMetadataRecord], int]:
        
        if not message_ids:
            return {}, 0
            
        metadata_headers = headers or GMAIL_METADATA_HEADERS
        
        metadata_map: dict[str, GmailMetadataRecord] = {}
        failed_count = 0
        
        def _request_chunk(chunk_ids):
            chunk_map = {}
            chunk_failures = 0
            
            def _callback(request_id, response, exception):
                nonlocal chunk_failures
                if exception is not None:
                    logger.warning("[GMAIL_METADATA_BATCH] Failed to fetch metadata for %s: %s", request_id, exception)
                    chunk_failures += 1
                else:
                    payload = response.get("payload", {})
                    response_headers = {
                        header["name"]: header.get("value", "")
                        for header in payload.get("headers", [])
                        if "name" in header
                    }
                    
                    record = GmailMetadataRecord(
                        id=response["id"],
                        thread_id=response.get("threadId"),
                        headers=response_headers,
                        label_ids=response.get("labelIds", []),
                        snippet=response.get("snippet", ""),
                    )
                    chunk_map[request_id] = record
                    
            batch = self._gmail_service.service.new_batch_http_request(callback=_callback)
            for msg_id in chunk_ids:
                request = self._gmail_service.service.users().messages().get(
                    userId="me",
                    id=msg_id,
                    format="metadata",
                    metadataHeaders=metadata_headers,
                )
                batch.add(request, request_id=msg_id)
                
            batch.execute()
            return chunk_map, chunk_failures
            
        chunk_size = 100
        
        def _execute_all():
            nonlocal failed_count
            for i in range(0, len(message_ids), chunk_size):
                chunk_ids = message_ids[i:i + chunk_size]
                chunk_map, chunk_failures = _request_chunk(chunk_ids)
                metadata_map.update(chunk_map)
                failed_count += chunk_failures
                
        await asyncio.to_thread(_execute_all)
        
        return metadata_map, failed_count