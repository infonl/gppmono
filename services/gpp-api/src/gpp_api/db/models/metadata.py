"""Metadata models: InformationCategory, Organisation, Theme, Topic."""

from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from gpp_api.db.models.base import Base, TimestampMixin, UUIDMixin


class OriginType(str, Enum):
    """Origin types for metadata entries."""

    WAARDELIJST = "waardelijst"
    ZELF_TOEGEVOEGD = "zelf_toegevoegd"


class OrganisationOrigin(str, Enum):
    """Origin types for organisations."""

    GEMEENTELIJST = "gemeentelijst"
    SOLIJST = "solijst"
    OORGLIJST = "oorglijst"
    ZELF_TOEGEVOEGD = "zelf_toegevoegd"


class ArchiveNomination(str, Enum):
    """Archive nomination options."""

    BLIJVEND_BEWAREN = "blijvend_bewaren"
    VERNIETIGEN = "vernietigen"


class InformationCategory(Base, UUIDMixin, TimestampMixin):
    """Information category (Informatiecategorie) for classifying publications."""

    __tablename__ = "information_category"

    # IRI identifying category in overheid.nl value list
    identifier: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Display names
    naam: Mapped[str] = mapped_column(String(80), nullable=False)
    naam_meervoud: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # Description and origin
    definitie: Mapped[str | None] = mapped_column(Text, nullable=True)
    omschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)
    oorsprong: Mapped[str] = mapped_column(
        String(15),
        default=OriginType.ZELF_TOEGEVOEGD.value,
        nullable=False,
    )

    # Ordering
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Retention policy fields
    bron_bewaartermijn: Mapped[str | None] = mapped_column(String(255), nullable=True)
    selectiecategorie: Mapped[str | None] = mapped_column(String(255), nullable=True)
    archiefnominatie: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bewaartermijn: Mapped[int | None] = mapped_column(Integer, nullable=True)  # years
    toelichting_bewaartermijn: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<InformationCategory(uuid={self.uuid}, naam={self.naam})>"

    @property
    def is_editable(self) -> bool:
        """Check if this category can be edited (not from value list)."""
        return self.oorsprong != OriginType.WAARDELIJST.value


class Organisation(Base, UUIDMixin, TimestampMixin):
    """Organisation that can publish or be responsible for publications."""

    __tablename__ = "organisation"

    # IRI identifying organisation in overheid.nl value list
    identifier: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Display name
    naam: Mapped[str] = mapped_column(String(255), nullable=False)

    # Origin type
    oorsprong: Mapped[str] = mapped_column(
        String(15),
        default=OrganisationOrigin.ZELF_TOEGEVOEGD.value,
        nullable=False,
    )

    # RSIN (Rechtspersonen en Samenwerkingsverbanden Informatienummer)
    rsin: Mapped[str | None] = mapped_column(String(9), nullable=True)

    # Active status - only active orgs can be selected as publisher
    is_actief: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<Organisation(uuid={self.uuid}, naam={self.naam})>"


class Theme(Base, UUIDMixin):
    """Theme for categorizing publications (hierarchical)."""

    __tablename__ = "theme"

    # IRI from overheid.nl value list
    identifier: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Display name
    naam: Mapped[str] = mapped_column(String(80), nullable=False)

    # Materialized path for tree structure
    # Format: "0001", "0001.0001", "0001.0001.0002"
    path: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    depth: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Parent reference (NULL for root nodes)
    parent_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<Theme(uuid={self.uuid}, naam={self.naam})>"


class Topic(Base, UUIDMixin, TimestampMixin):
    """Topic (Onderwerp) that can span multiple publications."""

    __tablename__ = "topic"

    # Display info
    officiele_titel: Mapped[str] = mapped_column(String(255), nullable=False)
    omschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Image for topic display
    afbeelding: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Publication status
    publicatiestatus: Mapped[str] = mapped_column(
        String(12),
        default="concept",
        nullable=False,
    )

    # Promotion flag - show in frontend highlights
    promoot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<Topic(uuid={self.uuid}, titel={self.officiele_titel})>"
