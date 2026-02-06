"""Audit trail utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from gpp_api.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AuditContext:
    """Audit context for tracking user actions."""

    user_id: str | None = None
    user_display_name: str | None = None
    action: str | None = None
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


def log_audit_event(
    action: str,
    resource_type: str,
    resource_id: str,
    user_id: str | None = None,
    user_display_name: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Log an audit event.

    Args:
        action: The action performed (create, update, delete, publish, revoke, etc.)
        resource_type: Type of resource (publication, document, etc.)
        resource_id: ID of the resource
        user_id: ID of the user performing the action
        user_display_name: Display name of the user
        details: Additional details about the action
    """
    logger.info(
        "audit_event",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        user_display_name=user_display_name,
        details=details or {},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
