"""User group models - Gebruikersgroep and junction tables."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gpp_app.db.models.base import Base


class Gebruikersgroep(Base):
    """User group model.

    Groups can have members (gebruikers) and value lists (waardelijsten).
    Members of a group can access publications that use the group's value lists.
    """

    __tablename__ = "gebruikersgroep"

    uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    naam: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    omschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    waardelijsten: Mapped[list[GebruikersgroepWaardelijst]] = relationship(
        "GebruikersgroepWaardelijst",
        back_populates="gebruikersgroep",
        cascade="all, delete-orphan",
    )
    gebruikers: Mapped[list[GebruikersgroepGebruiker]] = relationship(
        "GebruikersgroepGebruiker",
        back_populates="gebruikersgroep",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Gebruikersgroep(uuid={self.uuid}, naam={self.naam})>"


class GebruikersgroepWaardelijst(Base):
    """Junction table for group-waardelijst relationship."""

    __tablename__ = "gebruikersgroep_waardelijst"

    gebruikersgroep_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gebruikersgroep.uuid", ondelete="CASCADE"),
        primary_key=True,
    )

    # Waardelijst ID is a string identifier (e.g., information category UUID)
    waardelijst_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    # Relationship back to group
    gebruikersgroep: Mapped[Gebruikersgroep] = relationship(
        "Gebruikersgroep",
        back_populates="waardelijsten",
    )

    def __repr__(self) -> str:
        return f"<GebruikersgroepWaardelijst(group={self.gebruikersgroep_uuid}, waardelijst={self.waardelijst_id})>"


class GebruikersgroepGebruiker(Base):
    """Junction table for group-user relationship."""

    __tablename__ = "gebruikersgroep_gebruiker"

    gebruikersgroep_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gebruikersgroep.uuid", ondelete="CASCADE"),
        primary_key=True,
    )

    # User ID from OIDC (stored as string, case-insensitive lookup)
    gebruiker_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    # Relationship back to group
    gebruikersgroep: Mapped[Gebruikersgroep] = relationship(
        "Gebruikersgroep",
        back_populates="gebruikers",
    )

    def __repr__(self) -> str:
        return f"<GebruikersgroepGebruiker(group={self.gebruikersgroep_uuid}, user={self.gebruiker_id})>"
