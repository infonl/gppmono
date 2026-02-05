"""Pydantic models matching the DIWOO XSD schema (v0.9.8).

These models represent the DiWoo metadata structure for Dutch government documents
under the Wet open overheid (Woo).

Schema reference: https://standaarden.overheid.nl/diwoo/metadata/0.9.8/xsd/diwoo/diwoo-metadata.xsd
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from woo_hoo.models.enums import (
    DocumentRelatie,
    DocumentSoort,
    InformatieCategorie,
    RedenVerwijderingVervanging,
    SoortHandeling,
    Taal,
)


class TOOIResource(BaseModel):
    """Base model for TOOI-referenced resources with URI and label."""

    model_config = ConfigDict(populate_by_name=True)

    resource: HttpUrl = Field(..., description="TOOI URI identifying this resource")
    label: str = Field(..., description="Human-readable label in Dutch")


class Organisatie(TOOIResource):
    """Organization reference per DIWOO organisatieType.

    Organizations are identified by their TOOI URI from the organisatielijst
    (gemeentelijst, ministerielijst, provincielijst, etc.).
    """

    pass


class InformatieCategorieMeta(BaseModel):
    """Information category with TOOI reference.

    One of the 17 Woo categories from Artikel 3.3.
    """

    model_config = ConfigDict(populate_by_name=True)

    categorie: InformatieCategorie = Field(..., description="The Woo information category")

    @property
    def resource(self) -> str:
        """TOOI URI for this category."""
        return self.categorie.tooi_uri

    @property
    def label(self) -> str:
        """Human-readable Dutch label."""
        return self.categorie.label

    def model_dump_diwoo(self) -> dict:
        """Dump in DIWOO XML-compatible format."""
        return {"resource": self.resource, "label": self.label}


class DocumentSoortMeta(BaseModel):
    """Document type with TOOI reference."""

    model_config = ConfigDict(populate_by_name=True)

    soort: DocumentSoort = Field(..., description="Document type")

    @property
    def resource(self) -> str:
        return self.soort.tooi_uri

    @property
    def label(self) -> str:
        return self.soort.label


class ThemaMeta(TOOIResource):
    """Theme/topic with TOOI reference."""

    pass


class TitelCollectie(BaseModel):
    """Title collection per DIWOO titelcollectieType.

    Contains the official title (required) plus optional short and alternative titles.
    """

    model_config = ConfigDict(populate_by_name=True)

    officiele_titel: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The official title of the document (required)",
        alias="officieleTitel",
    )
    verkorte_titels: list[str] | None = Field(
        default=None,
        description="Shortened title(s)",
        alias="verkorteTitels",
    )
    alternatieve_titels: list[str] | None = Field(
        default=None,
        description="Alternative title(s)",
        alias="alternatieveTitels",
    )


class ClassificatieCollectie(BaseModel):
    """Classification collection per DIWOO classificatiecollectieType.

    Contains information categories (required) plus optional document types,
    themes, and keywords.
    """

    model_config = ConfigDict(populate_by_name=True)

    informatiecategorieen: Annotated[list[InformatieCategorieMeta], Field(min_length=1)] = Field(
        ...,
        description="At least one Woo information category (required)",
    )
    documentsoorten: list[DocumentSoortMeta] | None = Field(
        default=None,
        description="Document types",
    )
    themas: list[ThemaMeta] | None = Field(
        default=None,
        description="Themes/topics",
    )
    trefwoorden: list[str] | None = Field(
        default=None,
        description="Keywords (free text)",
    )


class SoortHandelingMeta(BaseModel):
    """Handling type with TOOI reference."""

    model_config = ConfigDict(populate_by_name=True)

    handeling: SoortHandeling = Field(..., description="Type of document handling")

    @property
    def resource(self) -> str:
        return self.handeling.tooi_uri

    @property
    def label(self) -> str:
        return self.handeling.label


class DocumentHandeling(BaseModel):
    """Document handling/action per DIWOO documenthandelingType.

    Records when and by whom a document action (e.g., vaststelling, publicatie) occurred.
    """

    model_config = ConfigDict(populate_by_name=True)

    soort_handeling: SoortHandelingMeta = Field(
        ...,
        description="Type of handling action (required)",
        alias="soortHandeling",
    )
    at_time: datetime = Field(
        ...,
        description="When the handling occurred (required)",
        alias="atTime",
    )
    was_associated_with: Organisatie | None = Field(
        default=None,
        description="Organization that performed the action",
        alias="wasAssociatedWith",
    )


class Geldigheid(BaseModel):
    """Validity period per DIWOO geldigheidType."""

    model_config = ConfigDict(populate_by_name=True)

    begindatum: datetime | None = Field(default=None, description="Start of validity period")
    einddatum: datetime | None = Field(default=None, description="End of validity period")


class TaalMeta(BaseModel):
    """Language with TOOI reference."""

    model_config = ConfigDict(populate_by_name=True)

    taal: Taal = Field(default=Taal.NL, description="Document language")

    @property
    def resource(self) -> str:
        return self.taal.tooi_uri

    @property
    def label(self) -> str:
        return self.taal.label


class FormatMeta(TOOIResource):
    """File format with TOOI reference."""

    pass


class DocumentVerwijzing(BaseModel):
    """Reference to another document."""

    model_config = ConfigDict(populate_by_name=True)

    resource: str | None = Field(default=None, description="URI/identifier of referenced document")
    label: str = Field(..., description="Title or description of referenced document")


class DocumentRelatieMeta(BaseModel):
    """Document relationship type with TOOI reference."""

    model_config = ConfigDict(populate_by_name=True)

    relatie: DocumentRelatie = Field(..., description="Type of relationship")

    @property
    def resource(self) -> str:
        return self.relatie.tooi_uri

    @property
    def label(self) -> str:
        return self.relatie.label


class DocumentRelatieItem(BaseModel):
    """A relationship to another document."""

    model_config = ConfigDict(populate_by_name=True)

    role: DocumentRelatieMeta = Field(..., description="The relationship type")
    relation: DocumentVerwijzing = Field(..., description="The related document")


class RedenVerwijderingVervangingMeta(BaseModel):
    """Reason for removal/replacement with TOOI reference."""

    model_config = ConfigDict(populate_by_name=True)

    reden: RedenVerwijderingVervanging = Field(..., description="Reason for removal/replacement")

    @property
    def resource(self) -> str:
        return self.reden.tooi_uri

    @property
    def label(self) -> str:
        return self.reden.label


class ExtraMetadataVeld(BaseModel):
    """Extra metadata field (key-value pair)."""

    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(..., description="Field name")
    values: list[str] = Field(..., min_length=1, description="Field value(s)")


class ExtraMetadata(BaseModel):
    """Container for extra/custom metadata."""

    model_config = ConfigDict(populate_by_name=True)

    namespace: HttpUrl | None = Field(default=None, description="XML namespace for extra metadata")
    prefix: str | None = Field(default=None, description="Namespace prefix")
    extra_metadatavelden: list[ExtraMetadataVeld] = Field(
        ...,
        min_length=1,
        description="Extra metadata fields",
        alias="extraMetadatavelden",
    )


class DiWooMetadata(BaseModel):
    """Complete DIWOO metadata structure per DiWooType in the XSD schema.

    This is the main metadata model containing all fields from the DIWOO standard.

    Required fields:
    - publisher: Publishing organization
    - titelcollectie: Title information (with officieleTitel)
    - classificatiecollectie: Classification (with at least one informatiecategorie)
    - documenthandelingen: At least one document handling action

    All other fields are optional.
    """

    model_config = ConfigDict(populate_by_name=True)

    # Identifiers
    identifiers: list[str] | None = Field(
        default=None,
        description="Document identifiers (e.g., reference numbers)",
    )

    # Organizations (publisher is REQUIRED)
    publisher: Organisatie = Field(
        ...,
        description="Publishing organization (required)",
    )
    verantwoordelijke: Organisatie | None = Field(
        default=None,
        description="Responsible organization",
    )
    medeverantwoordelijken: list[Organisatie] | None = Field(
        default=None,
        description="Co-responsible organizations",
    )
    opsteller: Organisatie | None = Field(
        default=None,
        description="Drafting/compiling organization",
    )
    naam_opsteller: str | None = Field(
        default=None,
        description="Name of document author/compiler",
        alias="naamOpsteller",
    )

    # Titles (REQUIRED)
    titelcollectie: TitelCollectie = Field(
        ...,
        description="Title collection with official title (required)",
    )

    # Descriptions
    omschrijvingen: list[str] | None = Field(
        default=None,
        description="Document description(s)/summary",
    )

    # Classification (REQUIRED)
    classificatiecollectie: ClassificatieCollectie = Field(
        ...,
        description="Classification including information categories (required)",
    )

    # Dates and validity
    creatiedatum: date | None = Field(
        default=None,
        description="Document creation date",
    )
    geldigheid: Geldigheid | None = Field(
        default=None,
        description="Validity period",
    )

    # Document properties
    language: TaalMeta | None = Field(
        default=None,
        description="Document language",
    )
    format: FormatMeta | None = Field(
        default=None,
        description="File format",
    )
    aggregatiekenmerk: str | None = Field(
        default=None,
        description="Aggregation marker for grouping related documents",
    )

    # Document hierarchy
    is_part_of: DocumentVerwijzing | None = Field(
        default=None,
        description="Parent document reference",
        alias="isPartOf",
    )
    has_parts: list[DocumentVerwijzing] | None = Field(
        default=None,
        description="Child document references",
        alias="hasParts",
    )

    # Handling (REQUIRED - at least one)
    documenthandelingen: Annotated[list[DocumentHandeling], Field(min_length=1)] = Field(
        ...,
        description="Document handling actions (at least one required)",
    )

    # Relationships
    documentrelaties: list[DocumentRelatieItem] | None = Field(
        default=None,
        description="Relationships to other documents",
    )

    # Removal/replacement
    reden_verwijdering_vervanging: RedenVerwijderingVervangingMeta | None = Field(
        default=None,
        description="Reason for document removal or replacement",
        alias="redenVerwijderingVervanging",
    )

    def to_dict(self) -> dict:
        """Convert to dictionary with camelCase aliases.

        Returns:
            Dictionary representation with DIWOO-compliant field names.
        """
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string with camelCase aliases.

        Args:
            indent: JSON indentation level (default 2)

        Returns:
            JSON string representation with DIWOO-compliant field names.
        """
        import json

        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class Document(BaseModel):
    """Root Document element per DIWOO DocumentType.

    Can contain either DiWoo metadata or MDTO metadata, plus extra metadata.
    """

    model_config = ConfigDict(populate_by_name=True)

    diwoo: DiWooMetadata | None = Field(
        default=None,
        description="DiWoo metadata",
        alias="DiWoo",
    )
    extra_metadata: list[ExtraMetadata] | None = Field(
        default=None,
        description="Extra/custom metadata",
        alias="extraMetadata",
    )
