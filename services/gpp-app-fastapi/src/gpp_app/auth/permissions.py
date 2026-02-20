"""Authorization and permission helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, status

from gpp_app.auth.oidc import OdpcUser, get_current_user

if TYPE_CHECKING:
    pass


async def check_admin_access(
    user: Annotated[OdpcUser, Depends(get_current_user)],
) -> OdpcUser:
    """Dependency to check admin access.

    Args:
        user: Current authenticated user

    Returns:
        User if admin

    Raises:
        HTTPException: If user is not an admin
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# Type alias for admin-only endpoints
AdminUser = Annotated[OdpcUser, Depends(check_admin_access)]

# Type alias for authenticated user
AuthenticatedUser = Annotated[OdpcUser, Depends(get_current_user)]


async def get_user_waardelijsten(
    _user: OdpcUser,  # TODO: use when implemented
    _db_session: object,  # Will be AsyncSession when implemented
) -> list[str]:
    """Get the value lists (waardelijsten) accessible to a user.

    A user can access value lists through their group memberships.

    Args:
        _user: Current user
        _db_session: Database session

    Returns:
        List of value list identifiers the user can access
    """
    # TODO: Implement with database query
    # Query GebruikersgroepGebruiker for user.id
    # Join with GebruikersgroepWaardelijst to get accessible value lists
    return []


async def check_publication_access(
    user: OdpcUser,
    _publication_uuid: str,  # TODO: use when implemented
    _db_session: object,  # Will be AsyncSession when implemented
) -> bool:
    """Check if a user can access a specific publication.

    Access is granted if:
    - User is admin
    - User is the owner (eigenaar)
    - User is in the owner group (eigenaar_groep)
    - Publication uses value lists the user has access to

    Args:
        user: Current user
        _publication_uuid: Publication UUID to check (TODO: use when implemented)
        _db_session: Database session (TODO: use when implemented)

    Returns:
        True if user can access the publication
    """
    # TODO: Implement with database query
    # 1. Check if user.id matches publication.eigenaar.external_id
    # 2. Check if user is in publication.eigenaar_groep
    # 3. Check if publication's information categories are in user's accessible value lists

    return user.is_admin
