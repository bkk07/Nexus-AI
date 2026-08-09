from __future__ import annotations
import logging
import re
import base64
from typing import Any

from app.connectors.gmail.content_client import (
    GmailContentClient,
)
from app.connectors.gmail.metadata_client import (
    GmailMetadataClient,
)
from app.tools.gmail.service import GmailService


logger = logging.getLogger(__name__)


class GmailConnector:
    """
    Gmail connector exposed to the AI Service.

    Currently implemented:

        SEARCH
        FETCH

    Future operations:

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

        self._content = GmailContentClient(
            gmail_service
        )

    async def search(
        self,
        query: str = "",
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search Gmail and return metadata + snippet.

        This method does NOT fetch full email bodies.
        """

        logger.debug(
            "[GMAIL_SEARCH] query=%s requested_top_k=%s",
            query,
            top_k,
        )

        response = await self._metadata.list_message_refs(
            query=query,
            max_results=top_k,
        )

        message_refs = response.get(
            "messages",
            []
        )

        logger.debug(
            "[GMAIL_SEARCH] message_refs_returned=%s",
            len(message_refs),
        )

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

        logger.debug(
            "[GMAIL_SEARCH] final_result_count=%s",
            len(results),
        )

        return results

    def _decode_body(
        self,
        data: str,
    ) -> str:

        decoded = base64.urlsafe_b64decode(
            data.encode("UTF-8")
        )

        return decoded.decode(
            "utf-8",
            errors="replace",
        )

    def _collect_text_parts(
        self,
        payload: dict,
    ) -> tuple[list[str], list[str]]:

        plain_parts = []
        html_parts = []

        mime_type = payload.get(
            "mimeType"
        )

        data = payload.get(
            "body",
            {}
        ).get("data")

        if data:

            if mime_type == "text/plain":

                plain_parts.append(
                    self._decode_body(data)
                )

            elif mime_type == "text/html":

                html_parts.append(
                    self._decode_body(data)
                )

        for part in payload.get(
            "parts",
            []
        ):

            plain, html = (
                self._collect_text_parts(
                    part
                )
            )

            plain_parts.extend(plain)
            html_parts.extend(html)

        return plain_parts, html_parts

    def _extract_body(
        self,
        payload: dict,
    ) -> tuple[str, str | None]:

        plain_parts, html_parts = (
            self._collect_text_parts(
                payload
            )
        )

        if plain_parts:

            return (
                "\n\n".join(plain_parts),
                "text/plain",
            )

        if html_parts:

            return (
                "\n\n".join(html_parts),
                "text/html",
            )

        return "", None

    async def fetch(
        self,
        message_id: str,
    ) -> dict[str, Any]:
        """
        Fetch one Gmail message with full content.
        """

        logger.debug(
            "[GMAIL_FETCH] fetching_message_id=%s",
            message_id,
        )

        raw_message = (
            await self._content.get_message(
                message_id
            )
        )

        payload = raw_message.get(
            "payload",
            {}
        )

        headers = {}

        for header in payload.get(
            "headers",
            []
        ):

            name = header.get("name")
            value = header.get(
                "value",
                ""
            )

            if name:
                headers[name.lower()] = value

        body, body_type = self._extract_body(
            payload
        )

        logger.debug(
            "[GMAIL_FETCH] message_id=%s body_type=%s body_length=%s",
            raw_message.get("id", message_id),
            body_type,
            len(body) if isinstance(body, str) else 0,
        )

        return {
            "id": raw_message["id"],
            "thread_id": raw_message.get(
                "threadId"
            ),
            "from": headers.get(
                "from"
            ),
            "to": headers.get(
                "to"
            ),
            "subject": headers.get(
                "subject"
            ),
            "date": headers.get(
                "date"
            ),
            "snippet": raw_message.get(
                "snippet",
                ""
            ),
            "body": body,
            "body_type": body_type,
            "labels": raw_message.get(
                "labelIds",
                []
            ),
            "depth": "FULL_CONTENT",
        }
    async def count(
        self,
        query: str = "",
    ) -> int:
        """
        Count Gmail messages matching the query.

        Uses Gmail metadata/message references only.
        Does not fetch email content.

        Pagination is handled until all matching
        messages have been counted.
        """

        total = 0
        page_token = None
        page_number = 0

        while True:

            page_number += 1

            logger.debug(
                "[GMAIL_COUNT] query=%s page_number=%s page_size=%s page_token_present=%s",
                query,
                page_number,
                100,
                page_token is not None,
            )

            response = await self._metadata.list_message_refs(
                query=query,
                max_results=100,
                page_token=page_token,
            )

            messages = response.get(
                "messages",
                []
            )

            logger.debug(
                "[GMAIL_COUNT] query=%s page_number=%s page_result_count=%s",
                query,
                page_number,
                len(messages),
            )

            total += len(messages)

            page_token = response.get(
                "nextPageToken"
            )

            if not page_token:
                break

        logger.debug(
            "[GMAIL_COUNT] query=%s total=%s pages=%s",
            query,
            total,
            page_number,
        )

        return total
    def filter_emails(
        self,
        emails: list[dict[str, Any]],
        field: str,
        operator: str,
        value: str,
    ) -> list[dict[str, Any]]:
        """
        Filter already retrieved email records locally.

        Supported operators:
            - contains
            - equals

        Text comparisons are case-insensitive.
        List fields such as labels support contains/equals.
        """

        logger.debug(
            "[GMAIL_FILTER] email_count=%s field=%s operator=%s value_present=%s",
            len(emails),
            field,
            operator,
            bool(value),
        )

        filtered = []

        for email in emails:

            field_value = email.get(field)

            if field_value is None:
                continue

            # ---------------------------------------------
            # CONTAINS
            # ---------------------------------------------

            if operator == "contains":

                if isinstance(field_value, list):

                    matched = any(
                        str(value).lower()
                        in str(item).lower()
                        for item in field_value
                    )

                else:

                    matched = (
                        str(value).lower()
                        in str(field_value).lower()
                    )

            # ---------------------------------------------
            # EQUALS
            # ---------------------------------------------

            elif operator == "equals":

                if isinstance(field_value, list):

                    matched = value in field_value

                else:

                    matched = (
                        str(field_value).lower()
                        == str(value).lower()
                    )

            else:

                raise ValueError(
                    f"Unsupported filter operator: {operator}"
                )

            if matched:
                filtered.append(email)

        logger.debug(
            "[GMAIL_FILTER] filtered_count=%s",
            len(filtered),
        )

        return filtered

    def classify_email(
        self,
        email: dict[str, Any],
    ) -> dict[str, str]:
        """
        Classify an email using deterministic rules.

        Returns:
            category
            confidence
        """

        subject = email.get(
            "subject",
            ""
        ).lower()

        snippet = email.get(
            "snippet",
            ""
        ).lower()

        text = f"{subject} {snippet}"

        if "interview" in text:
            return {
                "category": "interview",
                "confidence": "high",
            }

        if (
            "rejected" in text
            or "regret" in text
        ):
            return {
                "category": "rejection",
                "confidence": "high",
            }

        if (
            "application" in text
            or "job" in text
        ):
            return {
                "category": "job",
                "confidence": "medium",
            }

        if (
            "unsubscribe" in text
            or "offer" in text
        ):
            return {
                "category": "promotion",
                "confidence": "medium",
            }

        return {
            "category": "other",
            "confidence": "low",
        }

    def classify_emails(
        self,
        emails: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Classify a collection of already retrieved emails.
        """

        logger.debug(
            "[GMAIL_CLASSIFY] email_count=%s",
            len(emails),
        )

        results = []

        for email in emails:

            classification = self.classify_email(
                email
            )

            results.append(
                {
                    **email,
                    "classification": classification[
                        "category"
                    ],
                    "classification_confidence": (
                        classification[
                            "confidence"
                        ]
                    ),
                }
            )

        logger.debug(
            "[GMAIL_CLASSIFY] classified_count=%s",
            len(results),
        )

        return results

    def extract_information(
        self,
        email: dict[str, Any],
        fields: list[str],
    ) -> dict[str, list[str]]:
        """
        Extract structured information from an email.

        Supported fields:
            - emails
            - urls
            - phones

        This version works on the email data already available.
        """

        logger.debug(
            "[GMAIL_EXTRACT] requested_fields=%s email_id=%s",
            fields,
            email.get("id"),
        )

        text = " ".join(
            [
                email.get("from", ""),
                email.get("to", ""),
                email.get("subject", ""),
                email.get("snippet", ""),
            ]
        )

        result: dict[str, list[str]] = {}

        if "emails" in fields:
            result["emails"] = re.findall(
                r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                text,
            )

        if "urls" in fields:
            result["urls"] = re.findall(
                r"https?://[^\s]+",
                text,
            )

        if "phones" in fields:
            result["phones"] = re.findall(
                r"\+?\d[\d\s().-]{7,}\d",
                text,
            )

        logger.debug(
            "[GMAIL_EXTRACT] extracted_keys=%s",
            list(result.keys()),
        )

        return result
    
def build_default_gmail_connector() -> GmailConnector:

    gmail_service = GmailService()

    return GmailConnector(
        gmail_service
    )