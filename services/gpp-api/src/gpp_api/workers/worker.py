"""Background worker process for processing tasks from Redis Streams."""

from __future__ import annotations

import asyncio
import signal
import socket
from typing import Any

from gpp_api.services.redis import close_redis, ensure_stream_group
from gpp_api.utils.logging import get_logger, setup_logging
from gpp_api.workers.queue import (
    acknowledge_task,
    claim_stale_tasks,
    get_pending_tasks,
)
from gpp_api.workers.tasks import get_handler, parse_task_payload

logger = get_logger(__name__)


class Worker:
    """Background worker that processes tasks from Redis Streams."""

    def __init__(
        self,
        consumer_name: str | None = None,
        batch_size: int = 10,
        block_timeout_ms: int = 5000,
        stale_claim_interval_seconds: int = 60,
    ) -> None:
        """Initialize the worker.

        Args:
            consumer_name: Unique consumer name (defaults to hostname)
            batch_size: Number of tasks to fetch per batch
            block_timeout_ms: How long to block waiting for tasks
            stale_claim_interval_seconds: How often to check for stale tasks
        """
        self.consumer_name = consumer_name or f"worker-{socket.gethostname()}"
        self.batch_size = batch_size
        self.block_timeout_ms = block_timeout_ms
        self.stale_claim_interval_seconds = stale_claim_interval_seconds

        self._running = False
        self._tasks_processed = 0
        self._tasks_failed = 0

    async def start(self) -> None:
        """Start the worker loop."""
        setup_logging()
        logger.info(
            "worker_starting",
            consumer_name=self.consumer_name,
            batch_size=self.batch_size,
        )

        # Ensure stream group exists
        await ensure_stream_group()

        self._running = True

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_shutdown)

        # Start the main loop and stale task recovery
        try:
            await asyncio.gather(
                self._process_loop(),
                self._claim_stale_loop(),
            )
        finally:
            await self._cleanup()

    def _handle_shutdown(self) -> None:
        """Handle shutdown signal."""
        logger.info("worker_shutdown_signal_received")
        self._running = False

    async def _cleanup(self) -> None:
        """Clean up resources."""
        await close_redis()
        logger.info(
            "worker_stopped",
            tasks_processed=self._tasks_processed,
            tasks_failed=self._tasks_failed,
        )

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                # Get pending tasks
                tasks = await get_pending_tasks(
                    consumer_name=self.consumer_name,
                    count=self.batch_size,
                    block_ms=self.block_timeout_ms,
                )

                for message_id, data in tasks:
                    if not self._running:
                        break
                    await self._process_task(message_id, data)

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error("worker_loop_error", error=str(e))
                await asyncio.sleep(1)  # Brief pause before retrying

    async def _claim_stale_loop(self) -> None:
        """Periodically claim stale tasks from dead workers."""
        while self._running:
            try:
                await asyncio.sleep(self.stale_claim_interval_seconds)

                if not self._running:
                    break

                # Claim stale tasks (idle > 60 seconds)
                stale_tasks = await claim_stale_tasks(
                    consumer_name=self.consumer_name,
                    min_idle_time_ms=60000,
                    count=5,
                )

                for message_id, data in stale_tasks:
                    if not self._running:
                        break
                    await self._process_task(message_id, data)

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error("stale_claim_loop_error", error=str(e))

    async def _process_task(
        self,
        message_id: str,
        data: dict[str, str],
    ) -> None:
        """Process a single task.

        Args:
            message_id: Stream message ID
            data: Task data from stream
        """
        task_type, payload = parse_task_payload(data)

        logger.info(
            "task_processing",
            message_id=message_id,
            task_type=task_type,
        )

        handler = get_handler(task_type)
        if not handler:
            logger.warning(
                "unknown_task_type",
                message_id=message_id,
                task_type=task_type,
            )
            # Acknowledge unknown tasks to remove them
            await acknowledge_task(message_id)
            return

        try:
            await handler(payload)
            await acknowledge_task(message_id)
            self._tasks_processed += 1

            logger.info(
                "task_completed",
                message_id=message_id,
                task_type=task_type,
            )

        except Exception as e:
            self._tasks_failed += 1
            logger.error(
                "task_failed",
                message_id=message_id,
                task_type=task_type,
                error=str(e),
            )
            # Don't acknowledge - task will be retried
            # In production, implement retry limit and dead letter queue


async def run_worker() -> None:
    """Run the worker process."""
    worker = Worker()
    await worker.start()
