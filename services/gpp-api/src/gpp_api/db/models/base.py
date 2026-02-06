"""Base model and mixins for SQLAlchemy models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        # Convert CamelCase to snake_case
        name = cls.__name__
        return "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")


class IDMixin:
    """Mixin that adds an auto-incrementing bigint primary key (Django style)."""

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


class UUIDMixin:
    """Mixin that adds a UUID unique column (Django style - separate from PK)."""

    uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        default=uuid.uuid4,
        nullable=False,
        index=True,
    )


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""

    registratiedatum: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    laatst_gewijzigd_datum: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class VersionMixin:
    """Mixin for optimistic locking using version column."""

    version: Mapped[int] = mapped_column(default=1)

    __mapper_args__: dict[str, Any] = {"version_id_col": "version"}


@event.listens_for(Base, "before_update", propagate=True)
def receive_before_update(mapper: Any, connection: Any, target: Any) -> None:
    """Update laatst_gewijzigd_datum before update if the model has it."""
    if hasattr(target, "laatst_gewijzigd_datum"):
        target.laatst_gewijzigd_datum = datetime.now(timezone.utc)
