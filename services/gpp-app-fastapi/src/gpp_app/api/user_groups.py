"""User groups (Gebruikersgroepen) endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gpp_app.auth.oidc import OdpcUser, get_current_user
from gpp_app.auth.permissions import AdminUser
from gpp_app.db.engine import get_session
from gpp_app.db.models.user_groups import (
    Gebruikersgroep,
    GebruikersgroepGebruiker,
    GebruikersgroepWaardelijst,
)
from gpp_app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# Request/Response models
class GebruikersgroepCreate(BaseModel):
    """Request model for creating a user group."""

    naam: str
    omschrijving: str | None = None
    gekoppelde_waardelijsten: list[str] = []
    gekoppelde_gebruikers: list[str] = []


class GebruikersgroepUpdate(BaseModel):
    """Request model for updating a user group."""

    naam: str
    omschrijving: str | None = None
    gekoppelde_waardelijsten: list[str] = []
    gekoppelde_gebruikers: list[str] = []


class GebruikersgroepResponse(BaseModel):
    """Response model for a user group."""

    uuid: UUID
    naam: str
    omschrijving: str | None
    gekoppelde_waardelijsten: list[str]
    gekoppelde_gebruikers: list[str]

    class Config:
        from_attributes = True


class GebruikersgroepListResponse(BaseModel):
    """Response model for list of user groups."""

    count: int
    results: list[GebruikersgroepResponse]


class MijnGebruikersgroepenResponse(BaseModel):
    """Response model for user's groups."""

    groups: list[GebruikersgroepResponse]
    waardelijsten: list[str]


# Database dependency
DbSession = Annotated[AsyncSession, Depends(get_session)]


@router.get("/gebruikersgroepen", response_model=GebruikersgroepListResponse)
async def list_user_groups(
    user: AdminUser,
    db: DbSession,
) -> GebruikersgroepListResponse:
    """List all user groups (admin only).

    Args:
        user: Admin user
        db: Database session

    Returns:
        List of all user groups
    """
    result = await db.execute(select(Gebruikersgroep))
    groups = result.scalars().all()

    response_groups = []
    for group in groups:
        # Get waardelijsten
        wl_result = await db.execute(
            select(GebruikersgroepWaardelijst.waardelijst_id).where(
                GebruikersgroepWaardelijst.gebruikersgroep_uuid == group.uuid
            )
        )
        waardelijsten = [str(row[0]) for row in wl_result.all()]

        # Get gebruikers
        gb_result = await db.execute(
            select(GebruikersgroepGebruiker.gebruiker_id).where(
                GebruikersgroepGebruiker.gebruikersgroep_uuid == group.uuid
            )
        )
        gebruikers = [row[0] for row in gb_result.all()]

        response_groups.append(
            GebruikersgroepResponse(
                uuid=group.uuid,
                naam=group.naam,
                omschrijving=group.omschrijving,
                gekoppelde_waardelijsten=waardelijsten,
                gekoppelde_gebruikers=gebruikers,
            )
        )

    return GebruikersgroepListResponse(
        count=len(response_groups),
        results=response_groups,
    )


@router.get("/gebruikersgroepen/{uuid}", response_model=GebruikersgroepResponse)
async def get_user_group(
    uuid: UUID,
    user: AdminUser,
    db: DbSession,
) -> GebruikersgroepResponse:
    """Get a single user group (admin only).

    Args:
        uuid: Group UUID
        user: Admin user
        db: Database session

    Returns:
        User group details
    """
    result = await db.execute(select(Gebruikersgroep).where(Gebruikersgroep.uuid == uuid))
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User group not found",
        )

    # Get waardelijsten
    wl_result = await db.execute(
        select(GebruikersgroepWaardelijst.waardelijst_id).where(
            GebruikersgroepWaardelijst.gebruikersgroep_uuid == group.uuid
        )
    )
    waardelijsten = [str(row[0]) for row in wl_result.all()]

    # Get gebruikers
    gb_result = await db.execute(
        select(GebruikersgroepGebruiker.gebruiker_id).where(
            GebruikersgroepGebruiker.gebruikersgroep_uuid == group.uuid
        )
    )
    gebruikers = [row[0] for row in gb_result.all()]

    return GebruikersgroepResponse(
        uuid=group.uuid,
        naam=group.naam,
        omschrijving=group.omschrijving,
        gekoppelde_waardelijsten=waardelijsten,
        gekoppelde_gebruikers=gebruikers,
    )


@router.post("/gebruikersgroepen", response_model=GebruikersgroepResponse, status_code=status.HTTP_201_CREATED)
async def create_user_group(
    body: GebruikersgroepCreate,
    user: AdminUser,
    db: DbSession,
) -> GebruikersgroepResponse:
    """Create a new user group (admin only).

    Args:
        body: Group data
        user: Admin user
        db: Database session

    Returns:
        Created user group
    """
    # Check for duplicate name
    existing = await db.execute(select(Gebruikersgroep).where(Gebruikersgroep.naam == body.naam))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A group with this name already exists",
        )

    # Create group
    group = Gebruikersgroep(
        naam=body.naam,
        omschrijving=body.omschrijving,
    )
    db.add(group)
    await db.flush()

    # Add waardelijsten
    for wl_id in body.gekoppelde_waardelijsten:
        db.add(
            GebruikersgroepWaardelijst(
                gebruikersgroep_uuid=group.uuid,
                waardelijst_id=wl_id,
            )
        )

    # Add gebruikers
    for gb_id in body.gekoppelde_gebruikers:
        db.add(
            GebruikersgroepGebruiker(
                gebruikersgroep_uuid=group.uuid,
                gebruiker_id=gb_id,
            )
        )

    await db.commit()

    logger.info(
        "user_group_created",
        group_uuid=str(group.uuid),
        naam=group.naam,
        created_by=user.id,
    )

    return GebruikersgroepResponse(
        uuid=group.uuid,
        naam=group.naam,
        omschrijving=group.omschrijving,
        gekoppelde_waardelijsten=body.gekoppelde_waardelijsten,
        gekoppelde_gebruikers=body.gekoppelde_gebruikers,
    )


@router.put("/gebruikersgroepen/{uuid}", response_model=GebruikersgroepResponse)
async def update_user_group(
    uuid: UUID,
    body: GebruikersgroepUpdate,
    user: AdminUser,
    db: DbSession,
) -> GebruikersgroepResponse:
    """Update a user group (admin only).

    Args:
        uuid: Group UUID
        body: Updated group data
        user: Admin user
        db: Database session

    Returns:
        Updated user group
    """
    result = await db.execute(select(Gebruikersgroep).where(Gebruikersgroep.uuid == uuid))
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User group not found",
        )

    # Check for duplicate name (if changing)
    if body.naam != group.naam:
        existing = await db.execute(select(Gebruikersgroep).where(Gebruikersgroep.naam == body.naam))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A group with this name already exists",
            )

    # Update group
    group.naam = body.naam
    group.omschrijving = body.omschrijving

    # Delete existing waardelijsten and add new ones
    await db.execute(
        GebruikersgroepWaardelijst.__table__.delete().where(
            GebruikersgroepWaardelijst.gebruikersgroep_uuid == uuid
        )
    )
    for wl_id in body.gekoppelde_waardelijsten:
        db.add(
            GebruikersgroepWaardelijst(
                gebruikersgroep_uuid=uuid,
                waardelijst_id=wl_id,
            )
        )

    # Delete existing gebruikers and add new ones
    await db.execute(
        GebruikersgroepGebruiker.__table__.delete().where(
            GebruikersgroepGebruiker.gebruikersgroep_uuid == uuid
        )
    )
    for gb_id in body.gekoppelde_gebruikers:
        db.add(
            GebruikersgroepGebruiker(
                gebruikersgroep_uuid=uuid,
                gebruiker_id=gb_id,
            )
        )

    await db.commit()

    logger.info(
        "user_group_updated",
        group_uuid=str(uuid),
        naam=body.naam,
        updated_by=user.id,
    )

    return GebruikersgroepResponse(
        uuid=group.uuid,
        naam=group.naam,
        omschrijving=group.omschrijving,
        gekoppelde_waardelijsten=body.gekoppelde_waardelijsten,
        gekoppelde_gebruikers=body.gekoppelde_gebruikers,
    )


@router.delete("/gebruikersgroepen/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_group(
    uuid: UUID,
    user: AdminUser,
    db: DbSession,
) -> None:
    """Delete a user group (admin only).

    Args:
        uuid: Group UUID
        user: Admin user
        db: Database session
    """
    result = await db.execute(select(Gebruikersgroep).where(Gebruikersgroep.uuid == uuid))
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User group not found",
        )

    await db.delete(group)
    await db.commit()

    logger.info(
        "user_group_deleted",
        group_uuid=str(uuid),
        deleted_by=user.id,
    )


@router.get("/mijn-gebruikersgroepen", response_model=MijnGebruikersgroepenResponse)
async def get_my_groups(
    user: Annotated[OdpcUser, Depends(get_current_user)],
    db: DbSession,
) -> MijnGebruikersgroepenResponse:
    """Get the current user's groups and accessible value lists.

    Args:
        user: Current user
        db: Database session

    Returns:
        User's groups and accessible value lists
    """
    if not user.id:
        return MijnGebruikersgroepenResponse(groups=[], waardelijsten=[])

    # Find groups where user is a member (case-insensitive)
    result = await db.execute(
        select(GebruikersgroepGebruiker.gebruikersgroep_uuid).where(
            GebruikersgroepGebruiker.gebruiker_id.ilike(user.id)
        )
    )
    group_uuids = [row[0] for row in result.all()]

    if not group_uuids:
        return MijnGebruikersgroepenResponse(groups=[], waardelijsten=[])

    # Get group details
    groups_result = await db.execute(
        select(Gebruikersgroep).where(Gebruikersgroep.uuid.in_(group_uuids))
    )
    groups = groups_result.scalars().all()

    # Collect all waardelijsten
    all_waardelijsten: set[str] = set()
    response_groups = []

    for group in groups:
        # Get waardelijsten for this group
        wl_result = await db.execute(
            select(GebruikersgroepWaardelijst.waardelijst_id).where(
                GebruikersgroepWaardelijst.gebruikersgroep_uuid == group.uuid
            )
        )
        waardelijsten = [str(row[0]) for row in wl_result.all()]
        all_waardelijsten.update(waardelijsten)

        # Get gebruikers for this group
        gb_result = await db.execute(
            select(GebruikersgroepGebruiker.gebruiker_id).where(
                GebruikersgroepGebruiker.gebruikersgroep_uuid == group.uuid
            )
        )
        gebruikers = [row[0] for row in gb_result.all()]

        response_groups.append(
            GebruikersgroepResponse(
                uuid=group.uuid,
                naam=group.naam,
                omschrijving=group.omschrijving,
                gekoppelde_waardelijsten=waardelijsten,
                gekoppelde_gebruikers=gebruikers,
            )
        )

    return MijnGebruikersgroepenResponse(
        groups=response_groups,
        waardelijsten=list(all_waardelijsten),
    )
