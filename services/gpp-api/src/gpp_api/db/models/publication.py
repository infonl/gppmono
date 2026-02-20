"""Publication and Document models matching publicatiebank database schema."""

from __future__ import annotations

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
    Column,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gpp_api.db.models.base import Base, IDMixin, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from gpp_api.db.models.accounts import OrganisationMember, OrganisationUnit
    from gpp_api.db.models.metadata import InformationCategory, Organisation, Topic


class PublicationStatus(str, Enum):
    """Publication status options."""

    CONCEPT = "concept"
    GEPUBLICEERD = "gepubliceerd"
    INGETROKKEN = "ingetrokken"


# Association table for publication <-> information categories (M2M)
publication_categories = Table(
    "publications_publication_informatie_categorieen",
    Base.metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "publication_id",
        BigInteger,
        ForeignKey("publications_publication.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "informationcategory_id",
        BigInteger,
        ForeignKey("metadata_informationcategory.id", ondelete="CASCADE"),
        nullable=False,
    ),
)

# Association table for publication <-> topics (M2M)
publication_topics = Table(
    "publications_publication_onderwerpen",
    Base.metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column(
        "publication_id",
        BigInteger,
        ForeignKey("publications_publication.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "topic_id",
        BigInteger,
        ForeignKey("publications_topic.id", ondelete="CASCADE"),
        nullable=False,
    ),
)


class Publication(Base, IDMixin, UUIDMixin, TimestampMixin):
    """Publication model - container for documents."""

    __tablename__ = "publications_publication"

    # Titles and description
    officiele_titel: Mapped[str] = mapped_column(String(255), nullable=False)
    verkorte_titel: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    omschrijving: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Status
    publicatiestatus: Mapped[str] = mapped_column(
        String(12),
        default=PublicationStatus.CONCEPT.value,
        nullable=False,
        index=True,
    )

    # Organisational relationships (using integer FKs like Django)
    publisher_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("metadata_organisation.id"),
        nullable=True,
    )
    verantwoordelijke_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("metadata_organisation.id"),
        nullable=True,
    )
    opsteller_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("metadata_organisation.id"),
        nullable=True,
    )

    # Owner relationships (using integer FKs like Django)
    eigenaar_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("accounts_organisationmember.id"),
        nullable=False,
    )
    eigenaar_groep_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("accounts_organisationunit.id"),
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
    bron_bewaartermijn: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    selectiecategorie: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    archiefnominatie: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    archiefactiedatum: Mapped[date | None] = mapped_column(Date, nullable=True)
    toelichting_bewaartermijn: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Relationships
    publisher: Mapped[Organisation | None] = relationship(
        "Organisation",
        foreign_keys=[publisher_id],
        lazy="selectin",
    )
    verantwoordelijke: Mapped[Organisation | None] = relationship(
        "Organisation",
        foreign_keys=[verantwoordelijke_id],
        lazy="selectin",
    )
    opsteller: Mapped[Organisation | None] = relationship(
        "Organisation",
        foreign_keys=[opsteller_id],
        lazy="selectin",
    )
    eigenaar: Mapped[OrganisationMember] = relationship(
        "OrganisationMember",
        foreign_keys=[eigenaar_id],
        lazy="selectin",
    )
    eigenaar_groep: Mapped[OrganisationUnit | None] = relationship(
        "OrganisationUnit",
        foreign_keys=[eigenaar_groep_id],
        lazy="selectin",
    )

    # Many-to-many relationships
    informatie_categorieen: Mapped[list[InformationCategory]] = relationship(
        "InformationCategory",
        secondary=publication_categories,
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
        CheckConstraint(
            "publicatiestatus = 'concept' OR publicatiestatus = '' OR publisher_id IS NOT NULL",
            name="publisher_null_only_for_concept_or_blank",
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


class PublicationIdentifier(Base, IDMixin):
    """Additional identifiers for a publication."""

    __tablename__ = "publications_publicationidentifier"

    publicatie_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("publications_publication.id", ondelete="CASCADE"),
        nullable=False,
    )

    kenmerk: Mapped[str] = mapped_column(String(255), nullable=False)
    bron: Mapped[str] = mapped_column(String(100), nullable=False)

    publicatie: Mapped[Publication] = relationship(
        "Publication",
        back_populates="identifiers",
    )

    def __repr__(self) -> str:
        return f"<PublicationIdentifier(kenmerk={self.kenmerk}, bron={self.bron})>"


class Document(Base, IDMixin, UUIDMixin, TimestampMixin):
    """Document model - belongs to a publication."""

    __tablename__ = "publications_document"

    # Parent publication
    publicatie_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("publications_publication.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Owner
    eigenaar_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("accounts_organisationmember.id"),
        nullable=False,
    )

    # Legacy identifier (deprecated but kept for compatibility)
    identifier: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    # Titles and description
    officiele_titel: Mapped[str] = mapped_column(String(255), nullable=False)
    verkorte_titel: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    omschrijving: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Date fields
    creatiedatum: Mapped[date] = mapped_column(Date, nullable=False)
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

    # File metadata
    bestandsformaat: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    bestandsnaam: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    bestandsomvang: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Source URL if document originates from Documents API
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False, default="")

    # Status
    publicatiestatus: Mapped[str] = mapped_column(
        String(12),
        default=PublicationStatus.CONCEPT.value,
        nullable=False,
        index=True,
    )

    # OpenZaak Documents API integration
    # Note: document_service_id references zgw_consumers_service table but we don't
    # define that FK here since we're connecting to an existing publicatiebank database
    document_service_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    document_uuid: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )
    lock: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    upload_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Metadata strip timestamp
    metadata_gestript_op: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    publicatie: Mapped[Publication] = relationship(
        "Publication",
        back_populates="documenten",
    )
    eigenaar: Mapped[OrganisationMember] = relationship(
        "OrganisationMember",
        foreign_keys=[eigenaar_id],
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
        CheckConstraint(
            "(document_service_id IS NULL AND document_uuid IS NULL) OR "
            "(document_service_id IS NOT NULL AND document_uuid IS NOT NULL)",
            name="documents_api_reference",
        ),
        CheckConstraint(
            "bestandsomvang >= 0",
            name="publications_document_bestandsomvang_check",
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
        return self.document_service_id is not None and self.document_uuid is not None


class DocumentIdentifier(Base, IDMixin):
    """Additional identifiers for a document."""

    __tablename__ = "publications_documentidentifier"

    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("publications_document.id", ondelete="CASCADE"),
        nullable=False,
    )

    kenmerk: Mapped[str] = mapped_column(String(255), nullable=False)
    bron: Mapped[str] = mapped_column(String(100), nullable=False)

    document: Mapped[Document] = relationship(
        "Document",
        back_populates="identifiers",
    )

    def __repr__(self) -> str:
        return f"<DocumentIdentifier(kenmerk={self.kenmerk}, bron={self.bron})>"
