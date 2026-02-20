"""Redis client with lazy initialization and async context manager."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import redis.asyncio as redis

from gpp_api.config import get_settings
from gpp_api.utils.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = get_logger(__name__)

# Global Redis client (lazy init)
_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Get or create the Redis client.

    Returns:
        Redis client instance
    """
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("redis_client_initialized", url=settings.redis_url)
    return _redis_client


async def close_redis() -> None:
    """Close the Redis client."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("redis_client_closed")


@asynccontextmanager
async def redis_connection() -> AsyncGenerator[redis.Redis, None]:
    """Context manager for Redis connections.

    Yields:
        Redis client instance
    """
    client = await get_redis()
    try:
        yield client
    finally:
        # Don't close the connection here - it's shared
        pass


async def ping_redis() -> bool:
    """Check Redis connectivity.

    Returns:
        True if Redis is reachable, False otherwise
    """
    try:
        client = await get_redis()
        response = await client.ping()
        return response is True
    except Exception as e:
        logger.error("redis_ping_failed", error=str(e))
        return False


# Redis Streams helpers
STREAM_NAME = "gpp_tasks"
CONSUMER_GROUP = "gpp_workers"


async def ensure_stream_group() -> None:
    """Ensure the consumer group exists for the task stream."""
    client = await get_redis()
    try:
        await client.xgroup_create(
            name=STREAM_NAME,
            groupname=CONSUMER_GROUP,
            id="0",
            mkstream=True,
        )
        logger.info("stream_group_created", stream=STREAM_NAME, group=CONSUMER_GROUP)
    except redis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            # Group already exists
            logger.debug("stream_group_exists", stream=STREAM_NAME, group=CONSUMER_GROUP)
        else:
            raise


async def enqueue_task(task_type: str, payload: dict[str, Any]) -> str:
    """Add a task to the Redis Stream.

    Args:
        task_type: Type of task (e.g., "index_document", "sync_to_openzaak")
        payload: Task payload data

    Returns:
        Stream message ID
    """
    client = await get_redis()
    message_id = await client.xadd(
        STREAM_NAME,
        {
            "type": task_type,
            "payload": str(payload),  # Will be JSON-encoded by caller
        },
    )
    logger.info("task_enqueued", task_type=task_type, message_id=message_id)
    return message_id
