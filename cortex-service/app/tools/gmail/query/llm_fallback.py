"""Structured-output micro-prompt fallback for ambiguous Gmail queries."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class GmailQueryLLMOutput(BaseModel):
    after: Optional[str] = Field(None, description="YYYY/MM/DD or null")
    before: Optional[str] = Field(None, description="YYYY/MM/DD or null")
    from_: Optional[str] = Field(None, alias="from")
    subject: Optional[str] = None
    is_unread: bool = False
    is_starred: bool = False
    has_attachment: bool = False
    residual_keywords: List[str] = Field(default_factory=list)

class LLMQueryFallback:
    def __init__(self, llm_client, reference_datetime_provider):
        self._llm = llm_client
        self._now = reference_datetime_provider

    async def translate(self, nl_query: str) -> GmailQueryLLMOutput:
        ref = self._now()
        system_prompt = (
            "Translate the user's email search request into structured fields. "
            f"Today's reference date is {ref.date().isoformat()}. "
            "CRITICAL RULES:\n"
            "1. DO NOT set 'after' or 'before' dates unless the user explicitly mentions a timeframe (e.g., 'yesterday', 'last week', 'since Monday').\n"
            "2. If no time is mentioned, leave 'after' and 'before' null.\n"
            "3. Return ONLY fields you are confident about; leave others null/false.\n"
            "4. Never invent a sender, subject, or date constraint that is not explicitly stated."
        )
        
        # Leverages LangChain/Groq structured output
        response = await self._llm.with_structured_output(GmailQueryLLMOutput).ainvoke(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": nl_query},
            ]
        )
        return response