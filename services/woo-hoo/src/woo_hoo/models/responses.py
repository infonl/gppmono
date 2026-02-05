"""Response models for the woo-hoo API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from woo_hoo.models.diwoo import DiWooMetadata


class FieldConfidence(BaseModel):
    """Confidence score for a specific metadata field."""

    field_name: str = Field(..., description="Name of the field")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    reasoning: str | None = Field(default=None, description="Explanation for the confidence level")


class ConfidenceScores(BaseModel):
    """Confidence scores for generated metadata."""

    overall: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    fields: list[FieldConfidence] = Field(default_factory=list, description="Per-field confidence scores")


class MetadataSuggestion(BaseModel):
    """Generated metadata suggestion with confidence information."""

    metadata: DiWooMetadata = Field(..., description="Generated DIWOO-compliant metadata")
    confidence: ConfidenceScores = Field(..., description="Confidence scores for the suggestion")
    model_used: str = Field(..., description="LLM model that generated this suggestion")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")


class MetadataGenerationResponse(BaseModel):
    """Response from metadata generation endpoint."""

    success: bool = Field(..., description="Whether generation succeeded")
    request_id: str = Field(..., description="Unique request identifier")
    suggestion: MetadataSuggestion | None = Field(
        default=None,
        description="Generated metadata suggestion (present if success=true)",
    )
    error: str | None = Field(
        default=None,
        description="Error message (present if success=false)",
    )


class MetadataValidationResponse(BaseModel):
    """Response from metadata validation endpoint."""

    valid: bool = Field(..., description="Whether metadata is valid")
    errors: list[str] = Field(default_factory=list, description="Validation error messages")
    metadata: DiWooMetadata | None = Field(
        default=None,
        description="Validated metadata (present if valid=true)",
    )


class CategoryInfo(BaseModel):
    """Information about a Woo information category."""

    code: str = Field(..., description="Category code (enum name)")
    label: str = Field(..., description="Dutch label")
    artikel: str = Field(..., description="Woo article reference (e.g., '3.3.2e')")
    tooi_uri: str = Field(..., description="Full TOOI URI")


class CategoriesResponse(BaseModel):
    """Response listing all Woo information categories."""

    categories: list[CategoryInfo] = Field(..., description="All 17 Woo categories")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")


class ReadyResponse(BaseModel):
    """Readiness check response."""

    status: str = Field(..., description="Readiness status")
    openrouter_connected: bool = Field(..., description="OpenRouter API connectivity")


class ModelInfo(BaseModel):
    """Information about an LLM model."""

    id: str = Field(..., description="OpenRouter model ID (e.g., 'mistralai/mistral-large-2512')")
    name: str = Field(..., description="Human-readable model name")
    is_default: bool = Field(default=False, description="Whether this is the default model")
    is_eu_based: bool = Field(default=False, description="Whether model is hosted in EU (data sovereignty)")
    warning: str | None = Field(
        default=None,
        description="Warning message for non-EU models regarding data sovereignty",
    )

    def model_post_init(self, _context: object) -> None:
        """Add warning for non-EU models."""
        if not self.is_eu_based and self.warning is None:
            object.__setattr__(
                self,
                "warning",
                "Non-EU model: Data may be processed outside the EU. "
                "Consider using Mistral AI models for Dutch government data sovereignty compliance.",
            )


class ModelsResponse(BaseModel):
    """Response listing available LLM models."""

    default_model: str = Field(..., description="Default model ID (EU-based)")
    recommended_models: list[ModelInfo] = Field(
        ..., description="Recommended models for metadata extraction. EU-based models listed first."
    )
    eu_recommendation: str = Field(
        default=(
            "For Dutch government documents, EU-based models (Mistral AI) are strongly recommended "
            "for data sovereignty compliance under GDPR and Dutch privacy regulations."
        ),
        description="EU data sovereignty recommendation",
    )
    note: str = Field(
        default="Any valid OpenRouter model ID can be used via the 'model' parameter.",
        description="Usage note",
    )
