"""LLM provider abstractions shared across the application."""

from abc import ABC, abstractmethod


class LLMProviderError(Exception):
    """Base exception for provider failures."""


class LLMAuthenticationError(LLMProviderError):
    """Raised when authentication with the provider fails."""


class LLMNetworkError(LLMProviderError):
    """Raised when the provider cannot be reached."""


class LLMServiceError(LLMProviderError):
    """Raised when the provider returns an unexpected failure."""


class LLMProvider(ABC):
    """Abstract chat interface used by the application layer."""

    @abstractmethod
    async def chat(self, prompt: str) -> str:
        """Return the generated text for the supplied prompt."""

        raise NotImplementedError

