"""Organisation endpoints."""

from __future__ import annotations

import uuid as uuid_module
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from gpp_api.api.deps import get_db
from gpp_api.db.models import Organisation

router = APIRouter()


class OrganisationResponse(BaseModel):
    """Response model for an organisation."""

    uuid: uuid_module.UUID
    identifier: str
    naam: str
    oorsprong: str
    rsin: str
    is_actief: bool = Field(serialization_alias="isActief")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class OrganisationListResponse(BaseModel):
    """Response model for list of organisations."""

    count: int
    results: list[OrganisationResponse]


@router.get("/organisaties", response_model=OrganisationListResponse)
async def list_organisations(
    db: Annotated[AsyncSession, Depends(get_db)],
    is_actief: bool | None = Query(None, alias="isActief"),
) -> OrganisationListResponse:
    """List all organisations.

    Args:
        db: Database session
        is_actief: Optional filter for active organisations

    Returns:
        List of organisations
    """
    query = select(Organisation).order_by(Organisation.naam)

    if is_actief is not None:
        query = query.where(Organisation.is_actief == is_actief)

    # Get count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    count = count_result.scalar() or 0

    # Get results
    result = await db.execute(query)
    organisations = result.scalars().all()

    return OrganisationListResponse(
        count=count,
        results=[OrganisationResponse.model_validate(org) for org in organisations],
    )


@router.get("/organisaties/{org_uuid}", response_model=OrganisationResponse)
async def get_organisation(
    org_uuid: uuid_module.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganisationResponse:
    """Get a single organisation by UUID.

    Args:
        org_uuid: Organisation UUID
        db: Database session

    Returns:
        Organisation details
    """
    query = select(Organisation).where(Organisation.uuid == org_uuid)
    result = await db.execute(query)
    organisation = result.scalar_one_or_none()

    if not organisation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation with UUID {org_uuid} not found",
        )

    return OrganisationResponse.model_validate(organisation)
