"""Metadata models: InformationCategory, Organisation, Theme, Topic."""

from __future__ import annotations

from enum import Enum

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from gpp_api.db.models.base import Base, IDMixin, TimestampMixin, UUIDMixin


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


class InformationCategory(Base, IDMixin, UUIDMixin):
    """Information category (Informatiecategorie) for classifying publications."""

    # Use publicatiebank table name for compatibility
    __tablename__ = "metadata_informationcategory"

    # IRI identifying category in overheid.nl value list
    identifier: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Display names
    naam: Mapped[str] = mapped_column(String(80), nullable=False)
    naam_meervoud: Mapped[str] = mapped_column(String(80), nullable=False, default="")

    # Description and origin
    definitie: Mapped[str] = mapped_column(Text, nullable=False, default="")
    omschrijving: Mapped[str] = mapped_column(Text, nullable=False, default="")
    oorsprong: Mapped[str] = mapped_column(
        String(15),
        default=OriginType.ZELF_TOEGEVOEGD.value,
        nullable=False,
    )

    # Ordering
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Retention policy fields (NOT NULL in DB, empty string allowed)
    bron_bewaartermijn: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    selectiecategorie: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    archiefnominatie: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    bewaartermijn: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    toelichting_bewaartermijn: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def __repr__(self) -> str:
        return f"<InformationCategory(uuid={self.uuid}, naam={self.naam})>"

    @property
    def is_editable(self) -> bool:
        """Check if this category can be edited (not from value list)."""
        return self.oorsprong != OriginType.WAARDELIJST.value


class Organisation(Base, IDMixin, UUIDMixin):
    """Organisation that can publish or be responsible for publications."""

    # Use publicatiebank table name for compatibility
    __tablename__ = "metadata_organisation"

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

    # RSIN (Rechtspersonen en Samenwerkingsverbanden Informatienummer) - NOT NULL in DB
    rsin: Mapped[str] = mapped_column(String(9), nullable=False, default="")

    # Active status - only active orgs can be selected as publisher
    is_actief: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<Organisation(uuid={self.uuid}, naam={self.naam})>"


class Theme(Base, IDMixin, UUIDMixin):
    """Theme for categorizing publications (hierarchical)."""

    # Use publicatiebank table name for compatibility
    __tablename__ = "metadata_theme"

    # IRI from overheid.nl value list
    identifier: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Display name
    naam: Mapped[str] = mapped_column(String(80), nullable=False)

    # Materialized path for tree structure (django-treebeard style)
    # Format: "0001", "00010001", "000100010002"
    path: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    depth: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    numchild: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<Theme(uuid={self.uuid}, naam={self.naam})>"


class Topic(Base, IDMixin, UUIDMixin, TimestampMixin):
    """Topic (Onderwerp) that can span multiple publications."""

    # Use publicatiebank table name for compatibility
    __tablename__ = "publications_topic"

    # Display info
    officiele_titel: Mapped[str] = mapped_column(String(255), nullable=False)
    omschrijving: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Image for topic display (varchar(100) in DB, NOT NULL)
    afbeelding: Mapped[str] = mapped_column(String(100), nullable=False, default="")

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
