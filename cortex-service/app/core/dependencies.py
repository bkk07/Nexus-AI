"""FastAPI dependency providers for application services."""

from app.llm.base import LLMProvider
from app.llm.factory import get_llm as get_llm_factory


def get_llm() -> LLMProvider:
    """Return the configured LLM provider for dependency injection."""

    return get_llm_factory()
