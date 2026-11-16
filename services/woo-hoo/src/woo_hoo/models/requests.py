"""Request models for the woo-hoo API."""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl, field_validator

from woo_hoo.models.enums import DEFAULT_LLM_MODEL, LLMModel


class PublisherHint(BaseModel):
    """Hint about the publishing organization.

    Provides context to the LLM about which organization published the document.
    The TOOI URI is optional but helps with accurate metadata generation.
    """

    name: str = Field(..., min_length=1, description="Organization name")
    tooi_uri: HttpUrl | None = Field(
        default=None,
        description="TOOI URI for the organization (e.g., https://identifier.overheid.nl/tooi/id/gemeente/gm0363)",
    )


class DocumentContent(BaseModel):
    """Document content for metadata generation."""

    text: str = Field(
        ...,
        min_length=10,
        max_length=500_000_000,
        description="Extracted text content from the document",
    )
    filename: str | None = Field(
        default=None,
        description="Original filename (helps with type detection)",
    )
    source_url: HttpUrl | None = Field(
        default=None,
        description="URL where document was retrieved",
    )


class MetadataGenerationRequest(BaseModel):
    """Request to generate DIWOO-compliant metadata for a document."""

    document: DocumentContent = Field(
        ...,
        description="Document content to analyze",
    )
    publisher_hint: PublisherHint | None = Field(
        default=None,
        description="Hint about the publishing organization",
    )
    model: str = Field(
        default=DEFAULT_LLM_MODEL,
        description=(
            f"LLM model to use. Default: {DEFAULT_LLM_MODEL} (EU-based). "
            f"Recommended models: {', '.join(m.value for m in LLMModel)}. "
            "Any valid OpenRouter model ID is accepted."
        ),
    )
    include_confidence: bool = Field(
        default=True,
        description="Include confidence scores in response",
    )

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate that model ID has valid OpenRouter format."""
        if not LLMModel.is_valid_openrouter_model(v):
            raise ValueError(f"Invalid model ID format: {v}. Expected format: provider/model-name")
        return v


class MetadataValidationRequest(BaseModel):
    """Request to validate metadata against DIWOO schema."""

    metadata: dict = Field(
        ...,
        description="Metadata to validate",
    )
