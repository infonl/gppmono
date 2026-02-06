"""Publication and Document models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    Column,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gpp_api.db.models.base import Base, TimestampMixin, UUIDMixin, VersionMixin

if TYPE_CHECKING:
    from gpp_api.db.models.accounts import OrganisationMember, OrganisationUnit
    from gpp_api.db.models.metadata import InformationCategory, Organisation, Topic


class PublicationStatus(str, Enum):
    """Publication status options."""

    CONCEPT = "concept"
    GEPUBLICEERD = "gepubliceerd"
    INGETROKKEN = "ingetrokken"


# Association tables for many-to-many relationships
publication_information_categories = Table(
    "publication_information_categories",
    Base.metadata,
    Column(
        "publication_uuid",
        UUID(as_uuid=True),
        ForeignKey("publication.uuid", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "information_category_uuid",
        UUID(as_uuid=True),
        ForeignKey("information_category.uuid", ondelete="CASCADE"),
        primary_key=True,
    ),
)

publication_topics = Table(
    "publication_topics",
    Base.metadata,
    Column(
        "publication_uuid",
        UUID(as_uuid=True),
        ForeignKey("publication.uuid", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "topic_uuid",
        UUID(as_uuid=True),
        ForeignKey("topic.uuid", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Publication(Base, UUIDMixin, TimestampMixin, VersionMixin):
    """Publication model - container for documents."""

    __tablename__ = "publication"

    # Titles and description
    officiele_titel: Mapped[str] = mapped_column(String(255), nullable=False)
    verkorte_titel: Mapped[str | None] = mapped_column(String(255), nullable=True)
    omschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status - managed by state machine
    publicatiestatus: Mapped[str] = mapped_column(
        String(12),
        default=PublicationStatus.CONCEPT.value,
        nullable=False,
        index=True,
    )

    # Organisational relationships
    publisher_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisation.uuid"),
        nullable=True,
    )
    verantwoordelijke_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisation.uuid"),
        nullable=True,
    )
    opsteller_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisation.uuid"),
        nullable=True,
    )

    # Owner relationships
    eigenaar_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisation_member.uuid"),
        nullable=True,
    )
    eigenaar_groep_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisation_unit.uuid"),
        nullable=True,
    )

    # Temporal fields
    gepubliceerd_op: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ingetrokken_op: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    datum_begin_geldigheid: Mapped[date | None] = mapped_column(Date, nullable=True)
    datum_einde_geldigheid: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Retention/archiving fields
    bron_bewaartermijn: Mapped[str | None] = mapped_column(String(255), nullable=True)
    selectiecategorie: Mapped[str | None] = mapped_column(String(255), nullable=True)
    archiefnominatie: Mapped[str | None] = mapped_column(String(50), nullable=True)
    archiefactiedatum: Mapped[date | None] = mapped_column(Date, nullable=True)
    toelichting_bewaartermijn: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    publisher: Mapped[Organisation | None] = relationship(
        "Organisation",
        foreign_keys=[publisher_uuid],
        lazy="selectin",
    )
    verantwoordelijke: Mapped[Organisation | None] = relationship(
        "Organisation",
        foreign_keys=[verantwoordelijke_uuid],
        lazy="selectin",
    )
    opsteller: Mapped[Organisation | None] = relationship(
        "Organisation",
        foreign_keys=[opsteller_uuid],
        lazy="selectin",
    )
    eigenaar: Mapped[OrganisationMember | None] = relationship(
        "OrganisationMember",
        foreign_keys=[eigenaar_uuid],
        lazy="selectin",
    )
    eigenaar_groep: Mapped[OrganisationUnit | None] = relationship(
        "OrganisationUnit",
        foreign_keys=[eigenaar_groep_uuid],
        lazy="selectin",
    )

    # Many-to-many relationships
    informatie_categorieen: Mapped[list[InformationCategory]] = relationship(
        "InformationCategory",
        secondary=publication_information_categories,
        lazy="selectin",
    )
    onderwerpen: Mapped[list[Topic]] = relationship(
        "Topic",
        secondary=publication_topics,
        lazy="selectin",
    )

    # One-to-many: documents
    documenten: Mapped[list[Document]] = relationship(
        "Document",
        back_populates="publicatie",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # One-to-many: identifiers
    identifiers: Mapped[list[PublicationIdentifier]] = relationship(
        "PublicationIdentifier",
        back_populates="publicatie",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        # Publisher required when not in concept status
        CheckConstraint(
            "publicatiestatus = 'concept' OR publisher_uuid IS NOT NULL",
            name="publication_publisher_required_when_published",
        ),
    )

    def __repr__(self) -> str:
        return f"<Publication(uuid={self.uuid}, titel={self.officiele_titel}, status={self.publicatiestatus})>"

    @property
    def is_published(self) -> bool:
        """Check if publication is in published state."""
        return self.publicatiestatus == PublicationStatus.GEPUBLICEERD.value

    @property
    def is_revoked(self) -> bool:
        """Check if publication is in revoked state."""
        return self.publicatiestatus == PublicationStatus.INGETROKKEN.value

    @property
    def can_publish(self) -> bool:
        """Check if publication can be published."""
        return self.publicatiestatus in (
            PublicationStatus.CONCEPT.value,
            "",
        )

    @property
    def can_revoke(self) -> bool:
        """Check if publication can be revoked."""
        return self.publicatiestatus == PublicationStatus.GEPUBLICEERD.value


class PublicationIdentifier(Base):
    """Additional identifiers for a publication."""

    __tablename__ = "publication_identifier"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    publicatie_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("publication.uuid", ondelete="CASCADE"),
        nullable=False,
    )

    kenmerk: Mapped[str] = mapped_column(String(40), nullable=False)
    bron: Mapped[str] = mapped_column(String(40), nullable=False)

    publicatie: Mapped[Publication] = relationship(
        "Publication",
        back_populates="identifiers",
    )

    __table_args__ = (
        UniqueConstraint(
            "publicatie_uuid",
            "kenmerk",
            "bron",
            name="publication_identifier_unique",
        ),
    )

    def __repr__(self) -> str:
        return f"<PublicationIdentifier(kenmerk={self.kenmerk}, bron={self.bron})>"


class Document(Base, UUIDMixin, TimestampMixin, VersionMixin):
    """Document model - belongs to a publication."""

    __tablename__ = "document"

    # Parent publication
    publicatie_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("publication.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Titles and description
    officiele_titel: Mapped[str] = mapped_column(String(255), nullable=False)
    verkorte_titel: Mapped[str | None] = mapped_column(String(255), nullable=True)
    omschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status - managed by state machine
    publicatiestatus: Mapped[str] = mapped_column(
        String(12),
        default=PublicationStatus.CONCEPT.value,
        nullable=False,
        index=True,
    )

    # File metadata
    bestandsformaat: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bestandsnaam: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bestandsomvang: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Source URL if document originates from Documents API
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Legacy identifier (deprecated but kept for compatibility)
    identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Date fields
    creatiedatum: Mapped[date | None] = mapped_column(Date, nullable=True)
    ontvangstdatum: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    datum_ondertekend: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    gepubliceerd_op: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ingetrokken_op: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # OpenZaak Documents API integration
    document_service_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    document_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    lock: Mapped[str | None] = mapped_column(String(255), nullable=True)
    upload_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Owner
    eigenaar_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisation_member.uuid"),
        nullable=True,
    )

    # Relationships
    publicatie: Mapped[Publication] = relationship(
        "Publication",
        back_populates="documenten",
    )
    eigenaar: Mapped[OrganisationMember | None] = relationship(
        "OrganisationMember",
        foreign_keys=[eigenaar_uuid],
        lazy="selectin",
    )

    # One-to-many: identifiers
    identifiers: Mapped[list[DocumentIdentifier]] = relationship(
        "DocumentIdentifier",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        # Both document_service_url and document_uuid must be set or both null
        CheckConstraint(
            "(document_service_url IS NULL AND document_uuid IS NULL) OR "
            "(document_service_url IS NOT NULL AND document_uuid IS NOT NULL)",
            name="document_service_both_or_neither",
        ),
    )

    def __repr__(self) -> str:
        return f"<Document(uuid={self.uuid}, titel={self.officiele_titel}, status={self.publicatiestatus})>"

    @property
    def is_published(self) -> bool:
        """Check if document is in published state."""
        return self.publicatiestatus == PublicationStatus.GEPUBLICEERD.value

    @property
    def has_openzaak_document(self) -> bool:
        """Check if document is registered in OpenZaak."""
        return self.document_service_url is not None and self.document_uuid is not None


class DocumentIdentifier(Base):
    """Additional identifiers for a document."""

    __tablename__ = "document_identifier"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    document_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document.uuid", ondelete="CASCADE"),
        nullable=False,
    )

    kenmerk: Mapped[str] = mapped_column(String(40), nullable=False)
    bron: Mapped[str] = mapped_column(String(40), nullable=False)

    document: Mapped[Document] = relationship(
        "Document",
        back_populates="identifiers",
    )

    __table_args__ = (
        UniqueConstraint(
            "document_uuid",
            "kenmerk",
            "bron",
            name="document_identifier_unique",
        ),
    )

    def __repr__(self) -> str:
        return f"<DocumentIdentifier(kenmerk={self.kenmerk}, bron={self.bron})>"
