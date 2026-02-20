"""FastAPI dependencies for gpp-api."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from gpp_api.config import Settings, get_settings
from gpp_api.db.engine import get_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async for session in get_session():
        yield session


# Type aliases for common dependencies
DbSession = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


async def verify_api_key(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> str:
    """Verify API key from Authorization header.

    Args:
        authorization: Authorization header value
        settings: Application settings

    Returns:
        The validated API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    # Support both "Token <key>" and "Bearer <key>" formats
    parts = authorization.split(" ", 1)
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )

    scheme, token = parts
    if scheme.lower() not in ("token", "bearer"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization scheme",
        )

    if token not in settings.api_key_list:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return token


# Audit headers from BFF
async def get_audit_context(
    audit_user_id: Annotated[str | None, Header(alias="Audit-User-ID")] = None,
    audit_user_representation: Annotated[str | None, Header(alias="Audit-User-Representation")] = None,
    audit_remarks: Annotated[str | None, Header(alias="Audit-Remarks")] = None,
) -> dict[str, str | None]:
    """Extract audit context from headers.

    Args:
        audit_user_id: User ID from BFF
        audit_user_representation: User display name from BFF
        audit_remarks: Action description from BFF

    Returns:
        Dict with audit context
    """
    return {
        "user_id": audit_user_id,
        "user_display_name": audit_user_representation,
        "action": audit_remarks,
    }


AuditContext = Annotated[dict[str, str | None], Depends(get_audit_context)]
