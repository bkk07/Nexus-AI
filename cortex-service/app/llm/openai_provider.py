"""OpenAI-backed implementation of the LLM provider abstraction."""

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, AuthenticationError, OpenAIError, RateLimitError

from app.core.config import get_settings
from app.llm.base import LLMAuthenticationError, LLMNetworkError, LLMProvider, LLMServiceError


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class OpenAIProvider(LLMProvider):
    """Thin adapter around the OpenAI Chat Completions API."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise LLMAuthenticationError("OPENAI_API_KEY is missing or empty.")

        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = DEFAULT_OPENAI_MODEL

    async def chat(self, prompt: str) -> str:
        """Send a prompt to OpenAI and return the generated text."""

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
            )
        except AuthenticationError as exc:
            raise LLMAuthenticationError("Invalid OpenAI API key.") from exc
        except (APIConnectionError, APITimeoutError) as exc:
            raise LLMNetworkError("Failed to reach the OpenAI API.") from exc
        except RateLimitError as exc:
            raise LLMServiceError("OpenAI rate limit exceeded.") from exc
        except OpenAIError as exc:
            raise LLMServiceError("OpenAI request failed.") from exc

        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise LLMServiceError("OpenAI returned no generated text.")

        return content

