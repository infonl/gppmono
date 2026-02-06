"""Account models: OrganisationMember, OrganisationUnit."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from gpp_api.db.models.base import Base, IDMixin


class OrganisationMember(Base, IDMixin):
    """Organisation member - external user from OIDC.

    Members are created when users log in via OIDC.
    They can own publications.
    """

    # Match publicatiebank table name
    __tablename__ = "accounts_organisationmember"

    # External identifier (unique user identifier)
    identifier: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Display name
    naam: Mapped[str] = mapped_column(String(255), nullable=False)

    def __repr__(self) -> str:
        return f"<OrganisationMember(id={self.id}, identifier={self.identifier})>"


class OrganisationUnit(Base, IDMixin):
    """Organisation unit (logical group of members).

    Units can own publications - any member in the unit can manage them.
    Maps to "Gebruikersgroep" in the C# application.
    """

    # Match publicatiebank table name
    __tablename__ = "accounts_organisationunit"

    # External identifier (unique unit identifier)
    identifier: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Display name
    naam: Mapped[str] = mapped_column(String(255), nullable=False)

    def __repr__(self) -> str:
        return f"<OrganisationUnit(id={self.id}, identifier={self.identifier})>"
