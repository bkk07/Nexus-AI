from __future__ import annotations

import json
import os

from groq import Groq

from models import CalendarOperation, CalendarRequest
from prompts import SEARCH_PLANNER_SYSTEM_PROMPT
from dotenv import load_dotenv

load_dotenv()

class SearchPlanner:
    """
    Converts a natural-language Calendar SEARCH request
    into a typed semantic CalendarRequest.
    """

    def __init__(
        self,
        client: Groq | None = None,
        model: str | None = None,
    ) -> None:

        self._client = client or Groq(
            api_key=os.environ["GROQ_API_KEY"]
        )

        self._model = model or os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-20b",
        )

    def plan(
        self,
        question: str,
    ) -> CalendarRequest:

        if not question.strip():
            raise ValueError(
                "Search question cannot be empty."
            )

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": SEARCH_PLANNER_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": question,
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "calendar_search_request",
                    "strict": True,
                    "schema": self._schema(),
                },
            },
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError(
                "Groq returned an empty SEARCH plan."
            )

        data = json.loads(content)

        # Safety check: this planner is SEARCH-only.
        if data.get("operation") != "SEARCH":
            raise ValueError(
                "SEARCH planner returned a non-SEARCH operation."
            )

        return CalendarRequest.model_validate(data)

    @staticmethod
    def _schema() -> dict:
        """
        Groq strict structured-output schema.

        All fields are required.
        Nullable values are represented explicitly with null.
        """

        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["SEARCH"],
                },
                "query": {
                    "type": ["string", "null"],
                },
                "event_id": {
                    "type": ["string", "null"],
                },
                "date": {
                    "type": ["string", "null"],
                },
                "start_time": {
                    "type": ["string", "null"],
                },
                "end_time": {
                    "type": ["string", "null"],
                },
                "duration_minutes": {
                    "type": ["integer", "null"],
                },
                "purpose": {
                    "type": ["string", "null"],
                },
                "timezone": {
                    "type": "string",
                },
            },
            "required": [
                "operation",
                "query",
                "event_id",
                "date",
                "start_time",
                "end_time",
                "duration_minutes",
                "purpose",
                "timezone",
            ],
            "additionalProperties": False,
        }