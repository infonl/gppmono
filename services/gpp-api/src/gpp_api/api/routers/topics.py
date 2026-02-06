"""Topic endpoints."""

from __future__ import annotations

import uuid as uuid_module
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from gpp_api.api.deps import get_db
from gpp_api.db.models import Topic

router = APIRouter()


class TopicResponse(BaseModel):
    """Response model for a topic."""

    uuid: uuid_module.UUID
    officiele_titel: str = Field(serialization_alias="officieleTitel")
    omschrijving: str
    afbeelding: str
    publicatiestatus: str
    promoot: bool
    registratiedatum: datetime
    laatst_gewijzigd_datum: datetime = Field(serialization_alias="laatstGewijzigdDatum")

    class Config:
        from_attributes = True
        populate_by_name = True


class TopicListResponse(BaseModel):
    """Response model for list of topics."""

    count: int
    results: list[TopicResponse]


@router.get("/onderwerpen", response_model=TopicListResponse)
async def list_topics(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TopicListResponse:
    """List all topics.

    Args:
        db: Database session

    Returns:
        List of topics
    """
    query = select(Topic).order_by(Topic.officiele_titel)

    # Get count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    count = count_result.scalar() or 0

    # Get results
    result = await db.execute(query)
    topics = result.scalars().all()

    return TopicListResponse(
        count=count,
        results=[TopicResponse.model_validate(topic) for topic in topics],
    )


@router.get("/onderwerpen/{topic_uuid}", response_model=TopicResponse)
async def get_topic(
    topic_uuid: uuid_module.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TopicResponse:
    """Get a single topic by UUID.

    Args:
        topic_uuid: Topic UUID
        db: Database session

    Returns:
        Topic details
    """
    query = select(Topic).where(Topic.uuid == topic_uuid)
    result = await db.execute(query)
    topic = result.scalar_one_or_none()

    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic with UUID {topic_uuid} not found",
        )

    return TopicResponse.model_validate(topic)
