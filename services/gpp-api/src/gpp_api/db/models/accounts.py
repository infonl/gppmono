"""Account models: OrganisationMember, OrganisationUnit."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from gpp_api.db.models.base import Base, TimestampMixin, UUIDMixin


class OrganisationMember(Base, UUIDMixin, TimestampMixin):
    """Organisation member - external user from OIDC.

    Members are created when users log in via OIDC.
    They can own publications and be assigned to organisation units.
    """

    __tablename__ = "organisation_member"

    # External identifier from OIDC (sub claim or preferred_username)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Display name
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Email
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<OrganisationMember(uuid={self.uuid}, external_id={self.external_id})>"


class OrganisationUnit(Base, UUIDMixin, TimestampMixin):
    """Organisation unit (logical group of members).

    Units own publications - any member in the unit can manage them.
    Maps to "Gebruikersgroep" in the C# application.
    """

    __tablename__ = "organisation_unit"

    # Display name
    naam: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Description
    omschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<OrganisationUnit(uuid={self.uuid}, naam={self.naam})>"
