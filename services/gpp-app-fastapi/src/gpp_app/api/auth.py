"""Authentication endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.responses import RedirectResponse

from gpp_app.auth.oidc import (
    OdpcUser,
    get_current_user,
    get_optional_user,
    handle_callback,
    login_redirect,
    logout,
)
from gpp_app.config import Settings, get_settings

router = APIRouter()


class MeResponse(BaseModel):
    """Response model for /api/me endpoint."""

    is_logged_in: bool
    is_admin: bool
    id: str | None
    full_name: str | None
    email: str | None
    roles: list[str]


@router.get("/me", response_model=MeResponse)
async def get_me(
    user: Annotated[OdpcUser | None, Depends(get_optional_user)],
) -> MeResponse:
    """Get current user information.

    Returns user info if authenticated, otherwise returns not logged in status.

    Returns:
        Current user information
    """
    if user is None:
        return MeResponse(
            is_logged_in=False,
            is_admin=False,
            id=None,
            full_name=None,
            email=None,
            roles=[],
        )

    return MeResponse(
        is_logged_in=user.is_logged_in,
        is_admin=user.is_admin,
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        roles=user.roles,
    )


@router.get("/challenge")
async def challenge(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    """Initiate OIDC login flow.

    Redirects to OIDC provider for authentication.

    Returns:
        Redirect to OIDC provider
    """
    return await login_redirect(request, settings)


@router.get("/callback")
async def callback(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    """Handle OIDC callback.

    Processes the OIDC callback, stores user info in session,
    and redirects to home page.

    Returns:
        Redirect to home page
    """
    return await handle_callback(request, settings)


@router.get("/logoff")
async def logoff(request: Request) -> RedirectResponse:
    """Log out the current user.

    Clears the session and redirects to home page.

    Returns:
        Redirect to home page
    """
    return await logout(request)
