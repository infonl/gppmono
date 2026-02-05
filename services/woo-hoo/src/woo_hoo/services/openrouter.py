"""OpenRouter API client for LLM access.

Uses the official OpenRouter Python SDK to provide access to EU-based LLM models
(primarily Mistral), enabling data sovereignty compliance for Dutch government use cases.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from openrouter import OpenRouter
from pydantic import BaseModel

from woo_hoo.config import Settings, get_settings
from woo_hoo.utils.logging import get_logger
from woo_hoo.utils.retry import RetryConfig, with_retry

if TYPE_CHECKING:
    from openrouter.types.chat_completion_response import ChatCompletionResponse as SDKResponse

logger = get_logger(__name__)


@dataclass(frozen=True)
class OpenRouterModels:
    """Available OpenRouter models.

    EU-based models are preferred for Dutch government data sovereignty.
    """

    # EU-based models (preferred)
    MISTRAL_LARGE = "mistralai/mistral-large-2411"
    MISTRAL_SMALL = "mistralai/mistral-small-2501"
    MISTRAL_NEMO = "mistralai/mistral-nemo"

    # Fallback options (non-EU)
    CLAUDE_SONNET = "anthropic/claude-sonnet-4"
    GPT_4O = "openai/gpt-4o"


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str
    content: str


class ChatCompletionChoice(BaseModel):
    """A single completion choice."""

    index: int
    message: ChatMessage
    finish_reason: str | None = None


class ChatCompletionUsage(BaseModel):
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """OpenRouter chat completion response."""

    id: str
    model: str
    choices: list[ChatCompletionChoice]
    usage: ChatCompletionUsage | None = None


class OpenRouterClient:
    """Async client for OpenRouter API using the official SDK.

    Uses the OpenRouter Python SDK with async support for chat completions.
    Includes built-in retry logic for rate limits and transient errors.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the client.

        Args:
            settings: Application settings (uses get_settings() if not provided)
        """
        self.settings = settings or get_settings()
        self._client: OpenRouter | None = None
        self._retry_config = RetryConfig(
            max_attempts=self.settings.llm_max_retries,
            base_delay=1.0,
            max_delay=30.0,
        )

    def _get_client(self) -> OpenRouter:
        """Get or create the OpenRouter SDK client."""
        if self._client is None:
            self._client = OpenRouter(
                api_key=self.settings.openrouter_api_key,
                timeout_ms=int(self.settings.llm_timeout_seconds * 1000),
            )
        return self._client

    def _convert_response(self, sdk_response: SDKResponse) -> ChatCompletionResponse:
        """Convert SDK response to our internal response model."""
        choices = []
        for choice in sdk_response.choices or []:
            # SDK uses ROLE as class constant, not role as instance attribute
            msg = choice.message
            if msg:
                role = getattr(msg, "ROLE", None) or getattr(msg, "role", "assistant")
                content = msg.content or ""
            else:
                role = "assistant"
                content = ""
            message = ChatMessage(role=role, content=content)
            choices.append(
                ChatCompletionChoice(
                    index=choice.index,
                    message=message,
                    finish_reason=choice.finish_reason,
                )
            )

        usage = None
        if sdk_response.usage:
            usage = ChatCompletionUsage(
                prompt_tokens=sdk_response.usage.prompt_tokens,
                completion_tokens=sdk_response.usage.completion_tokens,
                total_tokens=sdk_response.usage.total_tokens,
            )

        return ChatCompletionResponse(
            id=sdk_response.id,
            model=sdk_response.model,
            choices=choices,
            usage=usage,
        )

    async def chat_completion(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> ChatCompletionResponse:
        """Send a chat completion request.

        Args:
            messages: List of chat messages
            model: Model to use (defaults to settings.default_model)
            temperature: Sampling temperature (defaults to settings.llm_temperature)
            max_tokens: Maximum tokens in response
            response_format: Response format (e.g., {"type": "json_object"})

        Returns:
            Chat completion response

        Raises:
            Exception: On non-retryable errors
            RetryExhaustedError: When all retry attempts fail
        """
        model = model or self.settings.default_model
        temperature = temperature if temperature is not None else self.settings.llm_temperature

        # Format messages for the SDK
        sdk_messages = [{"role": m.role, "content": m.content} for m in messages]

        async def _make_request() -> ChatCompletionResponse:
            start_time = time.perf_counter()
            client = self._get_client()

            # Use the async method from the SDK
            sdk_response = await client.chat.send_async(
                model=model,
                messages=sdk_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(
                "OpenRouter request completed",
                model=model,
                elapsed_ms=elapsed_ms,
            )

            return self._convert_response(sdk_response)

        return await with_retry(_make_request, self._retry_config)

    async def check_connectivity(self) -> bool:
        """Check if OpenRouter API is reachable.

        Returns:
            True if API is reachable, False otherwise
        """
        try:
            client = self._get_client()
            # Make a minimal request to check connectivity
            await client.chat.send_async(
                model="mistralai/mistral-nemo",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True
        except Exception as e:
            logger.warning("OpenRouter connectivity check failed", error=str(e))
            return False

    async def close(self) -> None:
        """Close the SDK client."""
        if self._client is not None:
            # The SDK uses context manager internally, but we can reset our reference
            self._client = None

    async def __aenter__(self) -> OpenRouterClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
