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
    ConfidenceScores,
    DocumentMetadataSuggestion,
    FieldConfidence,
    MetadataGenerationResponse,
    MetadataValidationResponse,
    ModelInfo,
    ModelsResponse,
    PublicationMetadataGenerationResponse,
    PublicationMetadataSuggestion,
)
from woo_hoo.services.document_extractor import DocumentExtractionError, extract_text_from_bytes
from woo_hoo.services.metadata_generator import MetadataGenerator
from woo_hoo.services.publicatiebank_client import (
    DocumentDownloadError,
    DocumentNotFoundError,
    PublicatiebankClient,
    PublicatiebankNotConfiguredError,
    PublicationNotFoundError,
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


def _compute_aggregated_confidence(document_suggestions: list[DocumentMetadataSuggestion]) -> ConfidenceScores:
    """Compute aggregated confidence scores from multiple document suggestions.

    Returns average overall confidence and aggregated field-level confidence.
    """
    if not document_suggestions:
        return ConfidenceScores(overall=0.0, fields=[])

    # Calculate average overall confidence
    overall_scores = [doc.confidence.overall for doc in document_suggestions]
    avg_overall = sum(overall_scores) / len(overall_scores)

    # Aggregate field-level confidence by field name
    field_scores: dict[str, list[float]] = {}
    field_reasoning: dict[str, list[str]] = {}

    for doc in document_suggestions:
        for field in doc.confidence.fields:
            if field.field_name not in field_scores:
                field_scores[field.field_name] = []
                field_reasoning[field.field_name] = []
            field_scores[field.field_name].append(field.confidence)
            if field.reasoning:
                field_reasoning[field.field_name].append(field.reasoning)

    # Build aggregated field confidence list
    aggregated_fields = [
        FieldConfidence(
            field_name=name,
            confidence=sum(scores) / len(scores),
            reasoning=f"Averaged from {len(scores)} document(s)"
            if len(scores) > 1
            else (field_reasoning[name][0] if field_reasoning[name] else None),
        )
        for name, scores in sorted(field_scores.items())
    ]

    return ConfidenceScores(overall=avg_overall, fields=aggregated_fields)


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


@router.post(
    "/generate-for-publication",
    response_model=PublicationMetadataGenerationResponse,
    summary="Generate metadata for a publication with multiple documents",
    description=(
        "Upload multiple documents and generate aggregated DIWOO-compliant metadata. "
        "Publication-level fields come from the first document. "
        "Keywords/themes are aggregated from all documents."
    ),
)
async def generate_metadata_for_publication(
    files: list[UploadFile] = File(..., description="PDF or text files to analyze"),
    publisher_name: str | None = Form(None, description="Publisher organization name"),
    publisher_uri: str | None = Form(None, description="Publisher TOOI URI"),
    model: str = Form(DEFAULT_LLM_MODEL, description="LLM model to use"),
) -> PublicationMetadataGenerationResponse:
    """Generate aggregated metadata for a publication from multiple uploaded files.

    Args:
        files: List of uploaded files (PDFs or text)
        publisher_name: Optional publisher organization name
        publisher_uri: Optional publisher TOOI URI
        model: LLM model to use

    Returns:
        Aggregated publication metadata with per-document suggestions
    """
    import time
    import uuid

    _check_api_key()
    request_id = str(uuid.uuid4())
    start_time = time.time()

    if not files:
        return PublicationMetadataGenerationResponse(
            success=False,
            request_id=request_id,
            error="No files provided",
        )

    # Validate model format
    if not LLMModel.is_valid_openrouter_model(model):
        return PublicationMetadataGenerationResponse(
            success=False,
            request_id=request_id,
            error=f"Invalid model ID format: {model}. Expected format: provider/model-name",
        )

    publisher_hint = None
    if publisher_name:
        publisher_hint = PublisherHint(
            name=publisher_name,
            tooi_uri=publisher_uri if publisher_uri else None,
        )

    document_suggestions: list[DocumentMetadataSuggestion] = []
    all_keywords: set[str] = set()
    documents_processed = 0
    documents_failed = 0
    first_metadata: DiWooMetadata | None = None

    generator = MetadataGenerator()
    try:
        for file in files:
            try:
                content = await file.read()
                text = extract_text_from_bytes(content, file.filename)

                request = MetadataGenerationRequest(
                    document=DocumentContent(text=text, filename=file.filename),
                    publisher_hint=publisher_hint,
                    model=model,
                )

                response = await generator.generate(request)

                if response.success and response.suggestion:
                    meta = response.suggestion.metadata
                    conf = response.suggestion.confidence

                    # Store first document's metadata as publication baseline
                    if first_metadata is None:
                        first_metadata = meta

                    # Aggregate keywords from all documents
                    if meta.classificatiecollectie and meta.classificatiecollectie.trefwoorden:
                        all_keywords.update(meta.classificatiecollectie.trefwoorden)

                    document_suggestions.append(
                        DocumentMetadataSuggestion(
                            document_filename=file.filename or "unknown",
                            metadata=meta,
                            confidence=conf,
                        )
                    )
                    documents_processed += 1
                else:
                    documents_failed += 1
                    logger.warning(
                        "Failed to generate metadata for file",
                        filename=file.filename,
                        error=response.error,
                    )

            except DocumentExtractionError as e:
                documents_failed += 1
                logger.warning(
                    "Failed to extract text from file",
                    filename=file.filename,
                    error=str(e),
                )
            except Exception as e:
                documents_failed += 1
                logger.error(
                    "Unexpected error processing file",
                    filename=file.filename,
                    error=str(e),
                )

    finally:
        await generator.close()

    processing_time_ms = int((time.time() - start_time) * 1000)

    if first_metadata is None:
        return PublicationMetadataGenerationResponse(
            success=False,
            request_id=request_id,
            documents_processed=documents_processed,
            documents_failed=documents_failed,
            error="No documents could be processed successfully",
        )

    # Update aggregated keywords in the publication metadata
    if all_keywords and first_metadata.classificatiecollectie:
        first_metadata.classificatiecollectie.trefwoorden = sorted(all_keywords)

    # Compute aggregated confidence scores
    overall_confidence = _compute_aggregated_confidence(document_suggestions)

    return PublicationMetadataGenerationResponse(
        success=True,
        request_id=request_id,
        suggestion=PublicationMetadataSuggestion(
            publication_metadata=first_metadata,
            overall_confidence=overall_confidence,
            document_suggestions=document_suggestions,
            aggregated_keywords=sorted(all_keywords),
            model_used=model,
            processing_time_ms=processing_time_ms,
        ),
        documents_processed=documents_processed,
        documents_failed=documents_failed,
    )


@router.post(
    "/generate-from-publication/{publication_uuid}",
    response_model=PublicationMetadataGenerationResponse,
    summary="Generate metadata from a publication in publicatiebank",
    description=(
        "Retrieve a publication and all its documents from GPP-publicatiebank "
        "and generate aggregated DIWOO-compliant metadata."
    ),
)
async def generate_metadata_from_publication(
    publication_uuid: str,
    publisher_name: str | None = None,
    publisher_uri: str | None = None,
    model: str = DEFAULT_LLM_MODEL,
) -> PublicationMetadataGenerationResponse:
    """Generate aggregated metadata for a publication from publicatiebank.

    Args:
        publication_uuid: UUID of the publication in publicatiebank
        publisher_name: Optional publisher organization name
        publisher_uri: Optional publisher TOOI URI
        model: LLM model to use

    Returns:
        Aggregated publication metadata with per-document suggestions
    """
    import time
    import uuid as uuid_module

    _check_api_key()
    request_id = str(uuid_module.uuid4())
    start_time = time.time()

    # Check if publicatiebank is configured
    client = PublicatiebankClient()
    if not client.is_configured:
        return PublicationMetadataGenerationResponse(
            success=False,
            request_id=request_id,
            error="GPP-publicatiebank is not configured. Set GPP_PUBLICATIEBANK_URL environment variable.",
        )

    # Validate model format
    if not LLMModel.is_valid_openrouter_model(model):
        return PublicationMetadataGenerationResponse(
            success=False,
            request_id=request_id,
            error=f"Invalid model ID format: {model}. Expected format: provider/model-name",
        )

    # Fetch publication with all documents
    try:
        publication = await client.get_publication_with_documents(publication_uuid)
    except PublicationNotFoundError as e:
        return PublicationMetadataGenerationResponse(
            success=False,
            request_id=request_id,
            error=str(e),
        )
    except PublicatiebankNotConfiguredError as e:
        return PublicationMetadataGenerationResponse(
            success=False,
            request_id=request_id,
            error=str(e),
        )
    except Exception as e:
        logger.error("Failed to fetch publication", publication_uuid=publication_uuid, error=str(e))
        return PublicationMetadataGenerationResponse(
            success=False,
            request_id=request_id,
            error=f"Failed to fetch publication: {e}",
        )
    finally:
        await client.close()

    if not publication.documents:
        return PublicationMetadataGenerationResponse(
            success=False,
            request_id=request_id,
            error="Publication has no downloadable documents",
        )

    publisher_hint = None
    if publisher_name:
        publisher_hint = PublisherHint(
            name=publisher_name,
            tooi_uri=publisher_uri if publisher_uri else None,
        )

    document_suggestions: list[DocumentMetadataSuggestion] = []
    all_keywords: set[str] = set()
    documents_processed = 0
    documents_failed = 0
    first_metadata: DiWooMetadata | None = None

    generator = MetadataGenerator()
    try:
        for doc in publication.documents:
            try:
                text = extract_text_from_bytes(doc.content, doc.bestandsnaam)

                request = MetadataGenerationRequest(
                    document=DocumentContent(text=text, filename=doc.bestandsnaam),
                    publisher_hint=publisher_hint,
                    model=model,
                )

                response = await generator.generate(request)

                if response.success and response.suggestion:
                    meta = response.suggestion.metadata
                    conf = response.suggestion.confidence

                    if first_metadata is None:
                        first_metadata = meta

                    if meta.classificatiecollectie and meta.classificatiecollectie.trefwoorden:
                        all_keywords.update(meta.classificatiecollectie.trefwoorden)

                    document_suggestions.append(
                        DocumentMetadataSuggestion(
                            document_uuid=doc.uuid,
                            document_filename=doc.bestandsnaam,
                            metadata=meta,
                            confidence=conf,
                        )
                    )
                    documents_processed += 1
                else:
                    documents_failed += 1
                    logger.warning(
                        "Failed to generate metadata for document",
                        document_uuid=doc.uuid,
                        error=response.error,
                    )

            except DocumentExtractionError as e:
                documents_failed += 1
                logger.warning(
                    "Failed to extract text from document",
                    document_uuid=doc.uuid,
                    error=str(e),
                )
            except Exception as e:
                documents_failed += 1
                logger.error(
                    "Unexpected error processing document",
                    document_uuid=doc.uuid,
                    error=str(e),
                )

    finally:
        await generator.close()

    processing_time_ms = int((time.time() - start_time) * 1000)

    if first_metadata is None:
        return PublicationMetadataGenerationResponse(
            success=False,
            request_id=request_id,
            documents_processed=documents_processed,
            documents_failed=documents_failed,
            error="No documents could be processed successfully",
        )

    if all_keywords and first_metadata.classificatiecollectie:
        first_metadata.classificatiecollectie.trefwoorden = sorted(all_keywords)

    # Compute aggregated confidence scores
    overall_confidence = _compute_aggregated_confidence(document_suggestions)

    logger.info(
        "Generated metadata for publication",
        publication_uuid=publication_uuid,
        documents_processed=documents_processed,
        documents_failed=documents_failed,
        processing_time_ms=processing_time_ms,
    )

    return PublicationMetadataGenerationResponse(
        success=True,
        request_id=request_id,
        suggestion=PublicationMetadataSuggestion(
            publication_metadata=first_metadata,
            overall_confidence=overall_confidence,
            document_suggestions=document_suggestions,
            aggregated_keywords=sorted(all_keywords),
            model_used=model,
            processing_time_ms=processing_time_ms,
        ),
        documents_processed=documents_processed,
        documents_failed=documents_failed,
    )
