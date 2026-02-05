"""Pydantic models for DIWOO metadata schema."""

from woo_hoo.models.diwoo import (
    ClassificatieCollectie,
    DiWooMetadata,
    DocumentHandeling,
    Geldigheid,
    Organisatie,
    TitelCollectie,
)
from woo_hoo.models.enums import (
    DocumentSoort,
    InformatieCategorie,
    SoortHandeling,
    Taal,
)
from woo_hoo.models.requests import MetadataGenerationRequest
from woo_hoo.models.responses import MetadataGenerationResponse

__all__ = [
    "ClassificatieCollectie",
    "DiWooMetadata",
    "DocumentHandeling",
    "DocumentSoort",
    "Geldigheid",
    "InformatieCategorie",
    "MetadataGenerationRequest",
    "MetadataGenerationResponse",
    "Organisatie",
    "SoortHandeling",
    "Taal",
    "TitelCollectie",
]
