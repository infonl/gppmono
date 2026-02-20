"""OIDC authentication with dev mode auto-login support."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, Request, status
from starlette.responses import RedirectResponse

from gpp_app.config import Settings, get_settings
from gpp_app.utils.logging import get_logger

logger = get_logger(__name__)

# OAuth client instance (lazy initialized)
_oauth: OAuth | None = None


def get_oauth(settings: Settings | None = None) -> OAuth:
    """Get or create the OAuth client.

    Args:
        settings: Optional settings override

    Returns:
        Configured OAuth client
    """
    global _oauth
    if _oauth is None:
        _oauth = OAuth()
        s = settings or get_settings()

        if s.oidc_authority:
            _oauth.register(
                name="oidc",
                server_metadata_url=f"{s.oidc_authority.rstrip('/')}/.well-known/openid-configuration",
                client_id=s.oidc_client_id,
                client_secret=s.oidc_client_secret,
                client_kwargs={
                    "scope": "openid profile email",
                },
            )
            logger.info("oauth_client_registered", authority=s.oidc_authority)
        else:
            logger.info("oauth_client_dev_mode", message="No OIDC authority configured, using dev auto-login")

    return _oauth


@dataclass
class OdpcUser:
    """User model extracted from OIDC claims or dev mode."""

    is_logged_in: bool
    is_admin: bool
    id: str | None
    full_name: str | None
    email: str | None
    roles: list[str]

    @classmethod
    def from_session(cls, session: dict, settings: Settings) -> OdpcUser:
        """Create user from session data.

        Args:
            session: Starlette session dict
            settings: Application settings

        Returns:
            OdpcUser instance
        """
        user_data = session.get("user", {})

        if not user_data:
            return cls(
                is_logged_in=False,
                is_admin=False,
                id=None,
                full_name=None,
                email=None,
                roles=[],
            )

        # Extract claims based on configured claim types
        user_id = user_data.get(settings.oidc_id_claim_type) or user_data.get("email")
        full_name = user_data.get(settings.oidc_name_claim_type) or user_data.get("name")
        email = user_data.get("email")

        # Roles can be a list or a single string
        roles_claim = user_data.get(settings.oidc_role_claim_type, [])
        roles = [roles_claim] if isinstance(roles_claim, str) else list(roles_claim) if roles_claim else []

        is_admin = settings.oidc_admin_role in roles

        return cls(
            is_logged_in=True,
            is_admin=is_admin,
            id=user_id,
            full_name=full_name,
            email=email,
            roles=roles,
        )

    @classmethod
    def dev_user(cls) -> OdpcUser:
        """Create a dev mode user (auto-login as admin).

        Returns:
            OdpcUser with admin privileges
        """
        return cls(
            is_logged_in=True,
            is_admin=True,
            id="dev-user",
            full_name="Development User",
            email="dev@localhost",
            roles=["odpc-admin"],
        )


async def get_current_user(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> OdpcUser:
    """FastAPI dependency to get the current user.

    In dev mode (no OIDC_AUTHORITY), returns a dev admin user.
    In production, extracts user from session.

    Args:
        request: FastAPI request
        settings: Application settings

    Returns:
        Current user

    Raises:
        HTTPException: If not authenticated in production mode
    """
    # Dev mode: auto-login as admin
    if settings.is_dev_mode:
        return OdpcUser.dev_user()

    # Production mode: extract from session
    user = OdpcUser.from_session(request.session, settings)

    if not user.is_logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return user


async def get_optional_user(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> OdpcUser | None:
    """FastAPI dependency to get optional current user.

    Returns None if not authenticated instead of raising an exception.

    Args:
        request: FastAPI request
        settings: Application settings

    Returns:
        Current user or None
    """
    if settings.is_dev_mode:
        return OdpcUser.dev_user()

    user = OdpcUser.from_session(request.session, settings)
    return user if user.is_logged_in else None


async def login_redirect(
    request: Request,
    settings: Settings,
) -> RedirectResponse:
    """Generate OIDC login redirect.

    Args:
        request: FastAPI request
        settings: Application settings

    Returns:
        Redirect response to OIDC provider
    """
    oauth = get_oauth(settings)

    if not settings.oidc_authority:
        # Dev mode - just redirect to home
        return RedirectResponse(url="/")

    redirect_uri = f"{settings.app_url.rstrip('/')}/api/callback"
    return await oauth.oidc.authorize_redirect(request, redirect_uri)


async def handle_callback(
    request: Request,
    settings: Settings,
) -> RedirectResponse:
    """Handle OIDC callback.

    Args:
        request: FastAPI request
        settings: Application settings

    Returns:
        Redirect response to home page
    """
    oauth = get_oauth(settings)

    if not settings.oidc_authority:
        return RedirectResponse(url="/")

    token = await oauth.oidc.authorize_access_token(request)
    user_info = token.get("userinfo", {})

    # Store user in session
    request.session["user"] = dict(user_info)

    logger.info(
        "user_logged_in",
        user_id=user_info.get(settings.oidc_id_claim_type),
    )

    return RedirectResponse(url="/")


async def logout(request: Request) -> RedirectResponse:
    """Clear session and redirect to home.

    Args:
        request: FastAPI request

    Returns:
        Redirect response
    """
    request.session.clear()
    logger.info("user_logged_out")
    return RedirectResponse(url="/")
