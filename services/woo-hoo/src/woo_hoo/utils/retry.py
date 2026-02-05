"""Retry utilities for resilient HTTP requests."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx

from woo_hoo.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    retryable_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504)


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""

    pass


async def with_retry[T](
    func: Callable[[], Awaitable[T]],
    config: RetryConfig | None = None,
) -> T:
    """Execute an async function with exponential backoff retry.

    Args:
        func: Async function to execute
        config: Retry configuration (uses defaults if not provided)

    Returns:
        Result of the function

    Raises:
        RetryExhaustedError: When all attempts fail
        httpx.HTTPStatusError: For non-retryable HTTP errors
    """
    if config is None:
        config = RetryConfig()

    last_exception: Exception | None = None

    for attempt in range(1, config.max_attempts + 1):
        try:
            return await func()

        except httpx.HTTPStatusError as e:
            last_exception = e

            if e.response.status_code not in config.retryable_status_codes:
                raise

            if attempt == config.max_attempts:
                break

            delay = min(
                config.base_delay * (config.exponential_base ** (attempt - 1)),
                config.max_delay,
            )

            logger.warning(
                "Retrying after HTTP error",
                attempt=attempt,
                max_attempts=config.max_attempts,
                status_code=e.response.status_code,
                delay_seconds=delay,
            )

            await asyncio.sleep(delay)

        except httpx.RequestError as e:
            last_exception = e

            if attempt == config.max_attempts:
                break

            delay = min(
                config.base_delay * (config.exponential_base ** (attempt - 1)),
                config.max_delay,
            )

            logger.warning(
                "Retrying after request error",
                attempt=attempt,
                max_attempts=config.max_attempts,
                error=str(e),
                delay_seconds=delay,
            )

            await asyncio.sleep(delay)

    raise RetryExhaustedError(f"All {config.max_attempts} attempts failed") from last_exception
