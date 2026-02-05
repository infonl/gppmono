"""Metadata generation and validation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from woo_hoo.config import get_settings
from woo_hoo.models.diwoo import DiWooMetadata
from woo_hoo.models.enums import DEFAULT_LLM_MODEL, InformatieCategorie, LLMModel
from woo_hoo.models.requests import (
    DocumentContent,
    MetadataGenerationRequest,
    MetadataValidationRequest,
    PublisherHint,
)
from woo_hoo.models.responses import (
    CategoriesResponse,
    CategoryInfo,
    MetadataGenerationResponse,
    MetadataValidationResponse,
    ModelInfo,
    ModelsResponse,
)
from woo_hoo.services.document_extractor import DocumentExtractionError, extract_text_from_bytes
from woo_hoo.services.metadata_generator import MetadataGenerator
from woo_hoo.services.publicatiebank_client import (
    DocumentDownloadError,
    DocumentNotFoundError,
    PublicatiebankClient,
    PublicatiebankNotConfiguredError,
)
from woo_hoo.utils.logging import get_logger


def _check_api_key() -> None:
    """Raise HTTPException if OpenRouter API key is not configured."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenRouter API key not configured. Set OPENROUTER_API_KEY environment variable.",
        )


router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])
logger = get_logger(__name__)


@router.post(
    "/generate",
    response_model=MetadataGenerationResponse,
    summary="Generate DIWOO-compliant metadata",
    description="Analyze document text and generate metadata suggestions compliant with DIWOO XSD schema.",
)
async def generate_metadata(
    request: MetadataGenerationRequest,
) -> MetadataGenerationResponse:
    """Generate DIWOO metadata from document text.

    Args:
        request: Document content and optional publisher hint

    Returns:
        Generated metadata with confidence scores
    """
    _check_api_key()
    generator = MetadataGenerator()
    try:
        return await generator.generate(request)
    finally:
        await generator.close()


@router.post(
    "/generate-from-file",
    response_model=MetadataGenerationResponse,
    summary="Generate metadata from uploaded file",
    description="Upload a PDF or text file and generate DIWOO-compliant metadata.",
)
async def generate_metadata_from_file(
    file: UploadFile = File(..., description="PDF or text file to analyze"),
    publisher_name: str | None = Form(None, description="Publisher organization name"),
    publisher_uri: str | None = Form(None, description="Publisher TOOI URI"),
    model: str = Form(DEFAULT_LLM_MODEL, description="LLM model to use (any valid OpenRouter model ID)"),
) -> MetadataGenerationResponse:
    """Generate DIWOO metadata from an uploaded file.

    Supports PDF and text files.

    Args:
        file: Uploaded file
        publisher_name: Optional publisher organization name
        publisher_uri: Optional publisher TOOI URI
        model: LLM model to use (defaults to Mistral Large)

    Returns:
        Generated metadata with confidence scores
    """
    _check_api_key()
    # Extract text from file
    try:
        content = await file.read()
        text = extract_text_from_bytes(content, file.filename)
    except DocumentExtractionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to extract text from file: {e}",
        ) from e

    # Validate model format
    if not LLMModel.is_valid_openrouter_model(model):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model ID format: {model}. Expected format: provider/model-name",
        )

    # Build request
    publisher_hint = None
    if publisher_name:
        publisher_hint = PublisherHint(
            name=publisher_name,
            tooi_uri=publisher_uri if publisher_uri else None,
        )

    request = MetadataGenerationRequest(
        document=DocumentContent(text=text, filename=file.filename),
        publisher_hint=publisher_hint,
        model=model,
    )

    generator = MetadataGenerator()
    try:
        return await generator.generate(request)
    finally:
        await generator.close()


@router.post(
    "/validate",
    response_model=MetadataValidationResponse,
    summary="Validate metadata against DIWOO schema",
    description="Validate provided metadata against DIWOO XSD schema requirements.",
)
async def validate_metadata(
    request: MetadataValidationRequest,
) -> MetadataValidationResponse:
    """Validate metadata against DIWOO schema.

    Args:
        request: Metadata to validate

    Returns:
        Validation result with any errors
    """
    try:
        validated = DiWooMetadata.model_validate(request.metadata)
        return MetadataValidationResponse(
            valid=True,
            metadata=validated,
        )
    except ValidationError as e:
        errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        return MetadataValidationResponse(
            valid=False,
            errors=errors,
        )


@router.get(
    "/categories",
    response_model=CategoriesResponse,
    summary="List all Woo information categories",
    description="Get all 17 Woo information categories with their codes, labels, and TOOI URIs.",
)
async def list_categories() -> CategoriesResponse:
    """List all 17 Woo information categories.

    Returns:
        List of categories with their details
    """
    categories = [
        CategoryInfo(
            code=cat.name,
            label=cat.label,
            artikel=cat.artikel,
            tooi_uri=cat.tooi_uri,
        )
        for cat in InformatieCategorie
    ]
    return CategoriesResponse(categories=categories)


@router.post(
    "/generate-from-publicatiebank",
    response_model=MetadataGenerationResponse,
    summary="Generate metadata from publicatiebank document",
    description="Retrieve a document from GPP-publicatiebank by UUID and generate DIWOO-compliant metadata.",
)
async def generate_metadata_from_publicatiebank(
    document_uuid: str,
    publisher_name: str | None = None,
    publisher_uri: str | None = None,
    model: str = DEFAULT_LLM_MODEL,
) -> MetadataGenerationResponse:
    """Generate DIWOO metadata from a document in publicatiebank.

    Args:
        document_uuid: UUID of the document in publicatiebank
        publisher_name: Optional publisher organization name
        publisher_uri: Optional publisher TOOI URI
        model: LLM model to use (defaults to Mistral Large)

    Returns:
        Generated metadata with confidence scores
    """
    _check_api_key()

    # Check if publicatiebank is configured
    client = PublicatiebankClient()
    if not client.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GPP-publicatiebank is not configured. Set GPP_PUBLICATIEBANK_URL environment variable.",
        )

    # Fetch document from publicatiebank
    try:
        document = await client.get_document(document_uuid)
    except PublicatiebankNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except DocumentDownloadError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e
    finally:
        await client.close()

    # Extract text from document content
    try:
        text = extract_text_from_bytes(document.content, document.bestandsnaam)
    except DocumentExtractionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract text from document: {e}",
        ) from e

    # Validate model format
    if not LLMModel.is_valid_openrouter_model(model):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model ID format: {model}. Expected format: provider/model-name",
        )

    # Build request
    publisher_hint = None
    if publisher_name:
        publisher_hint = PublisherHint(
            name=publisher_name,
            tooi_uri=publisher_uri if publisher_uri else None,
        )

    request = MetadataGenerationRequest(
        document=DocumentContent(text=text, filename=document.bestandsnaam),
        publisher_hint=publisher_hint,
        model=model,
    )

    logger.info(
        "Generating metadata from publicatiebank document",
        document_uuid=document_uuid,
        title=document.officiele_titel,
        filename=document.bestandsnaam,
    )

    generator = MetadataGenerator()
    try:
        return await generator.generate(request)
    finally:
        await generator.close()


@router.get(
    "/models",
    response_model=ModelsResponse,
    summary="List available LLM models",
    description=(
        "Get recommended LLM models for metadata extraction. "
        "EU-based models (Mistral AI) are recommended for data sovereignty compliance. "
        "Any valid OpenRouter model can be used."
    ),
)
async def list_models() -> ModelsResponse:
    """List available LLM models for metadata extraction.

    Returns:
        List of recommended models with the default highlighted.
        EU-based models are listed first for data sovereignty compliance.
    """
    eu_model_set = LLMModel.eu_models()

    # Separate EU and non-EU models, EU models first
    eu_models_list = [m for m in LLMModel if m in eu_model_set]
    non_eu_models_list = [m for m in LLMModel if m not in eu_model_set]

    recommended = []
    for model in eu_models_list + non_eu_models_list:
        recommended.append(
            ModelInfo(
                id=model.value,
                name=model.name.replace("_", " ").title(),
                is_default=model == LLMModel.default(),
                is_eu_based=model in eu_model_set,
            )
        )

    return ModelsResponse(
        default_model=DEFAULT_LLM_MODEL,
        recommended_models=recommended,
    )
