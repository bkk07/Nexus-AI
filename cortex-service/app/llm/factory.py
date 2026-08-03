"""Factory for resolving the active LLM provider implementation."""

from functools import lru_cache

from app.llm.base import LLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.groq_provider import GroqProvider



@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """Return the cached LLM provider instance."""
    return GroqProvider()


def get_llm() -> LLMProvider:
    """Expose the active provider for the rest of the application."""

    return get_llm_provider()

