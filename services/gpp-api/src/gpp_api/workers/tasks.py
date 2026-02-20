"""Task handlers for background processing."""

from __future__ import annotations

import json
from typing import Any, Callable, Coroutine

import httpx

from gpp_api.config import get_settings
from gpp_api.utils.logging import get_logger

logger = get_logger(__name__)

# Task handler registry
TaskHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
_handlers: dict[str, TaskHandler] = {}


def register_handler(task_type: str) -> Callable[[TaskHandler], TaskHandler]:
    """Decorator to register a task handler.

    Args:
        task_type: Type of task this handler processes

    Returns:
        Decorator function
    """

    def decorator(func: TaskHandler) -> TaskHandler:
        _handlers[task_type] = func
        logger.info("task_handler_registered", task_type=task_type)
        return func

    return decorator


def get_handler(task_type: str) -> TaskHandler | None:
    """Get the handler for a task type.

    Args:
        task_type: Type of task

    Returns:
        Handler function or None if not found
    """
    return _handlers.get(task_type)


@register_handler("index_document")
async def handle_index_document(payload: dict[str, Any]) -> None:
    """Index a document in gpp-zoeken.

    Args:
        payload: Task payload with document_uuid
    """
    document_uuid = payload.get("document_uuid")
    if not document_uuid:
        logger.error("index_document_missing_uuid", payload=payload)
        return

    settings = get_settings()
    if not settings.gpp_zoeken_url:
        logger.warning("gpp_zoeken_not_configured")
        return

    logger.info("index_document_start", document_uuid=document_uuid)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.gpp_zoeken_url}/api/v1/documents/index",
                json={"document_uuid": document_uuid},
                headers={
                    "Authorization": f"Bearer {settings.gpp_zoeken_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
            response.raise_for_status()

            logger.info(
                "index_document_success",
                document_uuid=document_uuid,
                status=response.status_code,
            )

    except httpx.HTTPStatusError as e:
        logger.error(
            "index_document_http_error",
            document_uuid=document_uuid,
            status=e.response.status_code,
            error=str(e),
        )
        raise

    except Exception as e:
        logger.error(
            "index_document_error",
            document_uuid=document_uuid,
            error=str(e),
        )
        raise


@register_handler("index_publication")
async def handle_index_publication(payload: dict[str, Any]) -> None:
    """Index a publication in gpp-zoeken.

    Args:
        payload: Task payload with publication_uuid
    """
    publication_uuid = payload.get("publication_uuid")
    if not publication_uuid:
        logger.error("index_publication_missing_uuid", payload=payload)
        return

    settings = get_settings()
    if not settings.gpp_zoeken_url:
        logger.warning("gpp_zoeken_not_configured")
        return

    logger.info("index_publication_start", publication_uuid=publication_uuid)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.gpp_zoeken_url}/api/v1/publications/index",
                json={"publication_uuid": publication_uuid},
                headers={
                    "Authorization": f"Bearer {settings.gpp_zoeken_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
            response.raise_for_status()

            logger.info(
                "index_publication_success",
                publication_uuid=publication_uuid,
                status=response.status_code,
            )

    except Exception as e:
        logger.error(
            "index_publication_error",
            publication_uuid=publication_uuid,
            error=str(e),
        )
        raise


@register_handler("remove_from_index")
async def handle_remove_from_index(payload: dict[str, Any]) -> None:
    """Remove a document or publication from gpp-zoeken index.

    Args:
        payload: Task payload with model and uuid
    """
    model = payload.get("model")
    uuid = payload.get("uuid")

    if not model or not uuid:
        logger.error("remove_from_index_missing_fields", payload=payload)
        return

    settings = get_settings()
    if not settings.gpp_zoeken_url:
        logger.warning("gpp_zoeken_not_configured")
        return

    logger.info("remove_from_index_start", model=model, uuid=uuid)

    try:
        endpoint = "documents" if model == "document" else "publications"

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{settings.gpp_zoeken_url}/api/v1/{endpoint}/{uuid}",
                headers={
                    "Authorization": f"Bearer {settings.gpp_zoeken_api_key}",
                },
                timeout=30.0,
            )
            response.raise_for_status()

            logger.info(
                "remove_from_index_success",
                model=model,
                uuid=uuid,
                status=response.status_code,
            )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # Already removed, that's fine
            logger.info(
                "remove_from_index_not_found",
                model=model,
                uuid=uuid,
            )
        else:
            logger.error(
                "remove_from_index_http_error",
                model=model,
                uuid=uuid,
                status=e.response.status_code,
                error=str(e),
            )
            raise

    except Exception as e:
        logger.error(
            "remove_from_index_error",
            model=model,
            uuid=uuid,
            error=str(e),
        )
        raise


@register_handler("sync_to_openzaak")
async def handle_sync_to_openzaak(payload: dict[str, Any]) -> None:
    """Sync a document to OpenZaak Documents API.

    Args:
        payload: Task payload with document_uuid and action
    """
    document_uuid = payload.get("document_uuid")
    action = payload.get("action", "create")

    if not document_uuid:
        logger.error("sync_to_openzaak_missing_uuid", payload=payload)
        return

    logger.info(
        "sync_to_openzaak_start",
        document_uuid=document_uuid,
        action=action,
    )

    # TODO: Implement actual sync logic with database lookup and OpenZaak client
    # This is a placeholder for the actual implementation

    logger.info(
        "sync_to_openzaak_success",
        document_uuid=document_uuid,
        action=action,
    )


def parse_task_payload(data: dict[str, str]) -> tuple[str, dict[str, Any]]:
    """Parse task type and payload from stream message data.

    Args:
        data: Raw message data from Redis Stream

    Returns:
        Tuple of (task_type, payload_dict)
    """
    task_type = data.get("type", "")
    payload_str = data.get("payload", "{}")

    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        logger.error("invalid_task_payload", payload_str=payload_str)
        payload = {}

    return task_type, payload
