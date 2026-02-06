"""Topic endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/onderwerpen")
async def list_topics() -> dict:
    """List all topics.

    Returns:
        List of topics
    """
    # TODO: Implement with database query
    return {"count": 0, "results": []}


@router.get("/onderwerpen/{uuid}")
async def get_topic(uuid: str) -> dict:
    """Get a single topic by UUID.

    Args:
        uuid: Topic UUID

    Returns:
        Topic details
    """
    # TODO: Implement with database query
    return {"uuid": uuid}
