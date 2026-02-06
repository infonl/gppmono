"""Redis Streams queue utilities."""

from __future__ import annotations

import json
from typing import Any

from gpp_api.services.redis import (
    CONSUMER_GROUP,
    STREAM_NAME,
    ensure_stream_group,
    get_redis,
)
from gpp_api.utils.logging import get_logger

logger = get_logger(__name__)


async def enqueue_task(task_type: str, payload: dict[str, Any]) -> str:
    """Add a task to the Redis Stream queue.

    Args:
        task_type: Type of task (e.g., "index_document", "sync_to_openzaak")
        payload: Task payload data

    Returns:
        Stream message ID
    """
    client = await get_redis()

    # Ensure consumer group exists
    await ensure_stream_group()

    # Serialize payload to JSON
    payload_json = json.dumps(payload)

    message_id = await client.xadd(
        STREAM_NAME,
        {
            "type": task_type,
            "payload": payload_json,
        },
    )

    logger.info(
        "task_enqueued",
        task_type=task_type,
        message_id=message_id,
        payload=payload,
    )

    return message_id


async def get_pending_tasks(
    consumer_name: str,
    count: int = 10,
    block_ms: int = 5000,
) -> list[tuple[str, dict[str, str]]]:
    """Read pending tasks from the stream.

    Args:
        consumer_name: Consumer name within the group
        count: Maximum number of messages to retrieve
        block_ms: How long to block waiting for messages

    Returns:
        List of (message_id, data) tuples
    """
    client = await get_redis()

    # Ensure consumer group exists
    await ensure_stream_group()

    # Read from stream as consumer
    messages = await client.xreadgroup(
        groupname=CONSUMER_GROUP,
        consumername=consumer_name,
        streams={STREAM_NAME: ">"},
        count=count,
        block=block_ms,
    )

    if not messages:
        return []

    # Parse messages - messages is [(stream_name, [(id, data), ...])]
    result = []
    for stream_name, stream_messages in messages:
        for message_id, data in stream_messages:
            result.append((message_id, data))

    return result


async def acknowledge_task(message_id: str) -> None:
    """Acknowledge a task as processed.

    Args:
        message_id: Stream message ID to acknowledge
    """
    client = await get_redis()

    await client.xack(STREAM_NAME, CONSUMER_GROUP, message_id)

    logger.debug("task_acknowledged", message_id=message_id)


async def get_pending_count() -> int:
    """Get the number of pending (unacknowledged) messages.

    Returns:
        Number of pending messages
    """
    client = await get_redis()

    try:
        info = await client.xpending(STREAM_NAME, CONSUMER_GROUP)
        return info.get("pending", 0) if info else 0
    except Exception:
        return 0


async def claim_stale_tasks(
    consumer_name: str,
    min_idle_time_ms: int = 60000,
    count: int = 10,
) -> list[tuple[str, dict[str, str]]]:
    """Claim stale tasks that haven't been acknowledged.

    This is useful for recovering tasks from crashed workers.

    Args:
        consumer_name: Consumer name to assign tasks to
        min_idle_time_ms: Minimum idle time before claiming
        count: Maximum number of tasks to claim

    Returns:
        List of (message_id, data) tuples for claimed tasks
    """
    client = await get_redis()

    try:
        # Get pending tasks info
        pending = await client.xpending_range(
            STREAM_NAME,
            CONSUMER_GROUP,
            min="-",
            max="+",
            count=count,
        )

        if not pending:
            return []

        # Filter for stale tasks and claim them
        result = []
        for entry in pending:
            message_id = entry.get("message_id")
            idle_time = entry.get("time_since_delivered", 0)

            if idle_time >= min_idle_time_ms and message_id:
                # Claim the message
                claimed = await client.xclaim(
                    STREAM_NAME,
                    CONSUMER_GROUP,
                    consumer_name,
                    min_idle_time_ms,
                    [message_id],
                )

                if claimed:
                    for msg_id, data in claimed:
                        result.append((msg_id, data))
                        logger.info(
                            "stale_task_claimed",
                            message_id=msg_id,
                            idle_time_ms=idle_time,
                        )

        return result

    except Exception as e:
        logger.error("claim_stale_tasks_error", error=str(e))
        return []
