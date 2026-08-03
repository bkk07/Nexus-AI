"""Groq-backed implementation of the LLM provider abstraction."""

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    OpenAIError,
    RateLimitError,
)

from app.core.config import get_settings
from app.llm.base import (
    LLMAuthenticationError,
    LLMNetworkError,
    LLMProvider,
    LLMServiceError,
)


DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


class GroqProvider(LLMProvider):
    """Thin adapter around the Groq OpenAI-compatible Chat Completions API."""

    def __init__(self) -> None:
        settings = get_settings()

        if not settings.groq_api_key:
            raise LLMAuthenticationError("GROQ_API_KEY is missing or empty.")

        self._client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )

        self._model = getattr(
            settings,
            "groq_model",
            DEFAULT_GROQ_MODEL,
        )

    async def chat(self, prompt: str) -> str:
        """Send a prompt to Groq and return the generated text."""

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.7,
            )

        except AuthenticationError as exc:
            raise LLMAuthenticationError("Invalid Groq API key.") from exc

        except (APIConnectionError, APITimeoutError) as exc:
            raise LLMNetworkError("Failed to reach the Groq API.") from exc

        except RateLimitError as exc:
            raise LLMServiceError("Groq rate limit exceeded.") from exc

        except OpenAIError as exc:
            raise LLMServiceError("Groq request failed.") from exc

        content = response.choices[0].message.content if response.choices else None

        if not content:
            raise LLMServiceError("Groq returned no generated text.")

        return content