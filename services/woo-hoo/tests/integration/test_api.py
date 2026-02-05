"""End-to-end API tests using httpx TestClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, async_client: AsyncClient):
        """Health endpoint should return healthy status."""
        response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "woo-hoo"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_readiness_check(self, async_client: AsyncClient):
        """Readiness endpoint should check OpenRouter connectivity."""
        # Mock the connectivity check to avoid real API calls
        with patch(
            "woo_hoo.api.routers.health.OpenRouterClient.check_connectivity",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = await async_client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "openrouter_connected" in data


class TestCategoriesEndpoint:
    """Tests for the categories endpoint."""

    @pytest.mark.asyncio
    async def test_list_categories(self, async_client: AsyncClient):
        """Should return all 17 Woo categories."""
        response = await async_client.get("/api/v1/metadata/categories")

        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) == 17

    @pytest.mark.asyncio
    async def test_category_structure(self, async_client: AsyncClient):
        """Each category should have required fields."""
        response = await async_client.get("/api/v1/metadata/categories")

        data = response.json()
        for cat in data["categories"]:
            assert "code" in cat
            assert "label" in cat
            assert "artikel" in cat
            assert "tooi_uri" in cat

    @pytest.mark.asyncio
    async def test_adviezen_category_present(self, async_client: AsyncClient):
        """ADVIEZEN category should be in the list."""
        response = await async_client.get("/api/v1/metadata/categories")

        data = response.json()
        codes = [cat["code"] for cat in data["categories"]]
        assert "ADVIEZEN" in codes


class TestValidateEndpoint:
    """Tests for the metadata validation endpoint."""

    @pytest.mark.asyncio
    async def test_validate_valid_metadata(
        self,
        async_client: AsyncClient,
        minimal_valid_metadata: dict,
    ):
        """Valid metadata should pass validation."""
        response = await async_client.post(
            "/api/v1/metadata/validate",
            json={"metadata": minimal_valid_metadata},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["errors"] == []

    @pytest.mark.asyncio
    async def test_validate_invalid_metadata(self, async_client: AsyncClient):
        """Invalid metadata should fail validation."""
        invalid_metadata = {
            "publisher": {"label": "Test"},  # Missing required 'resource'
        }

        response = await async_client.post(
            "/api/v1/metadata/validate",
            json={"metadata": invalid_metadata},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0


class TestGenerateEndpoint:
    """Tests for the metadata generation endpoint."""

    @pytest.mark.asyncio
    async def test_generate_requires_document(self, async_client: AsyncClient):
        """Generate endpoint should require document content."""
        response = await async_client.post(
            "/api/v1/metadata/generate",
            json={},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_generate_rejects_short_text(self, async_client: AsyncClient):
        """Should reject documents with very short text."""
        response = await async_client.post(
            "/api/v1/metadata/generate",
            json={"document": {"text": "short"}},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_generate_with_mock_llm(
        self,
        async_client: AsyncClient,
        sample_document_text: str,
        sample_publisher_hint: dict,
    ):
        """Test generation with mocked LLM response."""

        from woo_hoo.services.openrouter import ChatCompletionChoice, ChatCompletionResponse, ChatMessage

        # Mock XML response (XML is now the default mode)
        mock_xml_response = """<?xml version="1.0" encoding="UTF-8"?>
<diwoo:Document xmlns:diwoo="https://standaarden.overheid.nl/diwoo/metadata/">
  <diwoo:DiWoo>
    <diwoo:identifiers>
      <diwoo:identifier>ADV-2024-001</diwoo:identifier>
    </diwoo:identifiers>
    <diwoo:publisher resource="https://identifier.overheid.nl/tooi/id/gemeente/gm0363">Gemeente Amsterdam</diwoo:publisher>
    <diwoo:titelcollectie>
      <diwoo:officieleTitel>Advies inzake wijziging bestemmingsplan Centrum</diwoo:officieleTitel>
      <diwoo:verkorteTitel>Advies bestemmingsplan</diwoo:verkorteTitel>
    </diwoo:titelcollectie>
    <diwoo:omschrijvingen>
      <diwoo:omschrijving>Advies over wijziging bestemmingsplan</diwoo:omschrijving>
    </diwoo:omschrijvingen>
    <diwoo:classificatiecollectie>
      <diwoo:informatiecategorieen>
        <diwoo:informatiecategorie resource="https://identifier.overheid.nl/tooi/def/thes/kern/c_5ba23c01">Adviezen</diwoo:informatiecategorie>
      </diwoo:informatiecategorieen>
      <diwoo:documentsoorten>
        <diwoo:documentsoort resource="https://identifier.overheid.nl/tooi/def/thes/kern/c_advies">advies</diwoo:documentsoort>
      </diwoo:documentsoorten>
      <diwoo:trefwoorden>
        <diwoo:trefwoord>bestemmingsplan</diwoo:trefwoord>
        <diwoo:trefwoord>horeca</diwoo:trefwoord>
        <diwoo:trefwoord>centrum</diwoo:trefwoord>
      </diwoo:trefwoorden>
    </diwoo:classificatiecollectie>
    <diwoo:creatiedatum>2024-01-15</diwoo:creatiedatum>
    <diwoo:language resource="https://identifier.overheid.nl/tooi/def/thes/kern/c_nl">Nederlands</diwoo:language>
    <diwoo:documenthandelingen>
      <diwoo:documenthandeling>
        <diwoo:soortHandeling resource="https://identifier.overheid.nl/tooi/def/thes/kern/c_vaststelling">vaststelling</diwoo:soortHandeling>
        <diwoo:atTime>2024-01-15T10:00:00</diwoo:atTime>
        <diwoo:wasAssociatedWith resource="https://identifier.overheid.nl/tooi/id/gemeente/gm0363">Gemeente Amsterdam</diwoo:wasAssociatedWith>
      </diwoo:documenthandeling>
    </diwoo:documenthandelingen>
  </diwoo:DiWoo>
</diwoo:Document>"""

        # Create a properly typed mock response
        mock_response = ChatCompletionResponse(
            id="test-id",
            model="mistralai/mistral-large-2411",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=mock_xml_response),
                    finish_reason="stop",
                )
            ],
        )

        # Mock the OpenRouter client
        with patch("woo_hoo.services.metadata_generator.MetadataGenerator._get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat_completion = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            response = await async_client.post(
                "/api/v1/metadata/generate",
                json={
                    "document": {"text": sample_document_text},
                    "publisher_hint": sample_publisher_hint,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "suggestion" in data
        assert (
            data["suggestion"]["metadata"]["titelcollectie"]["officieleTitel"]
            == "Advies inzake wijziging bestemmingsplan Centrum"
        )


class TestModelsEndpoint:
    """Tests for the models endpoint."""

    @pytest.mark.asyncio
    async def test_list_models(self, async_client: AsyncClient):
        """Should return list of available models."""
        response = await async_client.get("/api/v1/metadata/models")

        assert response.status_code == 200
        data = response.json()
        assert "default_model" in data
        assert "recommended_models" in data
        assert "eu_recommendation" in data
        assert len(data["recommended_models"]) > 0

    @pytest.mark.asyncio
    async def test_models_have_required_fields(self, async_client: AsyncClient):
        """Each model should have required fields."""
        response = await async_client.get("/api/v1/metadata/models")

        data = response.json()
        for model in data["recommended_models"]:
            assert "id" in model
            assert "name" in model
            assert "is_default" in model
            assert "is_eu_based" in model

    @pytest.mark.asyncio
    async def test_eu_models_listed_first(self, async_client: AsyncClient):
        """EU-based models should be listed before non-EU models."""
        response = await async_client.get("/api/v1/metadata/models")

        data = response.json()
        models = data["recommended_models"]

        # Find first non-EU model index
        first_non_eu_idx = None
        for i, m in enumerate(models):
            if not m["is_eu_based"]:
                first_non_eu_idx = i
                break

        # All models before first non-EU should be EU-based
        if first_non_eu_idx is not None:
            for m in models[:first_non_eu_idx]:
                assert m["is_eu_based"] is True

    @pytest.mark.asyncio
    async def test_non_eu_models_have_warning(self, async_client: AsyncClient):
        """Non-EU models should have a warning message."""
        response = await async_client.get("/api/v1/metadata/models")

        data = response.json()
        for model in data["recommended_models"]:
            if not model["is_eu_based"]:
                assert model.get("warning") is not None
                assert "EU" in model["warning"]

    @pytest.mark.asyncio
    async def test_default_model_is_eu_based(self, async_client: AsyncClient):
        """The default model should be EU-based."""
        response = await async_client.get("/api/v1/metadata/models")

        data = response.json()
        default_model = data["default_model"]

        # Default should start with mistralai/
        assert default_model.startswith("mistralai/")


class TestGenerateFromPublicatiebankEndpoint:
    """Tests for the publicatiebank integration endpoint."""

    @pytest.mark.asyncio
    async def test_publicatiebank_not_configured(self, async_client: AsyncClient):
        """Should return 503 when publicatiebank is not configured."""
        response = await async_client.post(
            "/api/v1/metadata/generate-from-publicatiebank",
            params={"document_uuid": "550e8400-e29b-41d4-a716-446655440000"},
        )

        assert response.status_code == 503
        assert "GPP_PUBLICATIEBANK_URL" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_document_not_found(self, async_client: AsyncClient):
        """Should return 404 when document is not found in publicatiebank."""
        from woo_hoo.services.publicatiebank_client import DocumentNotFoundError

        with patch("woo_hoo.api.routers.metadata.PublicatiebankClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.is_configured = True
            mock_instance.get_document = AsyncMock(
                side_effect=DocumentNotFoundError("Document not found")
            )
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            response = await async_client.post(
                "/api/v1/metadata/generate-from-publicatiebank",
                params={"document_uuid": "550e8400-e29b-41d4-a716-446655440000"},
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_document_download_error(self, async_client: AsyncClient):
        """Should return 502 when document download fails."""
        from woo_hoo.services.publicatiebank_client import DocumentDownloadError

        with patch("woo_hoo.api.routers.metadata.PublicatiebankClient") as MockClient:
            mock_instance = AsyncMock()
            mock_instance.is_configured = True
            mock_instance.get_document = AsyncMock(
                side_effect=DocumentDownloadError("Upload not completed")
            )
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            response = await async_client.post(
                "/api/v1/metadata/generate-from-publicatiebank",
                params={"document_uuid": "550e8400-e29b-41d4-a716-446655440000"},
            )

        assert response.status_code == 502
        assert "Upload not completed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_generate_from_publicatiebank_with_mock(
        self,
        async_client: AsyncClient,
    ):
        """Test successful generation from publicatiebank with mocked responses."""
        from woo_hoo.services.openrouter import ChatCompletionChoice, ChatCompletionResponse, ChatMessage
        from woo_hoo.services.publicatiebank_client import PublicatiebankDocument

        # Create mock publicatiebank document (use .txt so content is treated as plain text)
        mock_document = PublicatiebankDocument(
            uuid="550e8400-e29b-41d4-a716-446655440000",
            officiele_titel="Test Document",
            verkorte_titel="Test",
            omschrijving="A test document",
            bestandsnaam="test.txt",
            bestandsformaat="text/plain",
            bestandsomvang=1024,
            publicatiestatus="published",
            content=b"This is a test document with sufficient content for the metadata generator to process. " * 20,
            kenmerken=[{"kenmerk": "TEST-001", "bron": "test-system"}],
        )

        # Mock XML response
        mock_xml_response = """<?xml version="1.0" encoding="UTF-8"?>
<diwoo:Document xmlns:diwoo="https://standaarden.overheid.nl/diwoo/metadata/">
  <diwoo:DiWoo>
    <diwoo:identifiers>
      <diwoo:identifier>TEST-001</diwoo:identifier>
    </diwoo:identifiers>
    <diwoo:publisher resource="https://identifier.overheid.nl/tooi/id/gemeente/gm0363">Test Publisher</diwoo:publisher>
    <diwoo:titelcollectie>
      <diwoo:officieleTitel>Test Document from Publicatiebank</diwoo:officieleTitel>
    </diwoo:titelcollectie>
    <diwoo:classificatiecollectie>
      <diwoo:informatiecategorieen>
        <diwoo:informatiecategorie resource="https://identifier.overheid.nl/tooi/def/thes/kern/c_5ba23c01">Adviezen</diwoo:informatiecategorie>
      </diwoo:informatiecategorieen>
    </diwoo:classificatiecollectie>
    <diwoo:documenthandelingen>
      <diwoo:documenthandeling>
        <diwoo:soortHandeling resource="https://identifier.overheid.nl/tooi/def/thes/kern/c_vaststelling">vaststelling</diwoo:soortHandeling>
        <diwoo:atTime>2024-01-15T10:00:00</diwoo:atTime>
      </diwoo:documenthandeling>
    </diwoo:documenthandelingen>
  </diwoo:DiWoo>
</diwoo:Document>"""

        mock_llm_response = ChatCompletionResponse(
            id="test-id",
            model="mistralai/mistral-large-2411",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=mock_xml_response),
                    finish_reason="stop",
                )
            ],
        )

        with (
            patch("woo_hoo.api.routers.metadata.PublicatiebankClient") as MockPubClient,
            patch("woo_hoo.services.metadata_generator.MetadataGenerator._get_client") as mock_get_llm,
        ):
            # Mock publicatiebank client
            mock_pub_instance = AsyncMock()
            mock_pub_instance.is_configured = True
            mock_pub_instance.get_document = AsyncMock(return_value=mock_document)
            mock_pub_instance.close = AsyncMock()
            MockPubClient.return_value = mock_pub_instance

            # Mock LLM client
            mock_llm_client = AsyncMock()
            mock_llm_client.chat_completion = AsyncMock(return_value=mock_llm_response)
            mock_get_llm.return_value = mock_llm_client

            response = await async_client.post(
                "/api/v1/metadata/generate-from-publicatiebank",
                params={"document_uuid": "550e8400-e29b-41d4-a716-446655440000"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "suggestion" in data
        assert data["suggestion"]["metadata"]["titelcollectie"]["officieleTitel"] == "Test Document from Publicatiebank"


# Tests for multi-file publication metadata generation endpoint


@pytest.mark.asyncio
async def test_generate_for_publication_no_files(async_client: AsyncClient):
    """Should return error when no files are provided."""
    response = await async_client.post(
        "/api/v1/metadata/generate-for-publication",
        files=[],
    )

    # FastAPI returns 422 for missing required files
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_for_publication_invalid_model(async_client: AsyncClient):
    """Should return error for invalid model format."""
    files = [("files", ("test.txt", b"Test content " * 100, "text/plain"))]

    response = await async_client.post(
        "/api/v1/metadata/generate-for-publication",
        files=files,
        data={"model": "invalid-model-format"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "Invalid model ID format" in data["error"]


@pytest.mark.asyncio
async def test_generate_for_publication_with_mock(async_client: AsyncClient):
    """Test successful multi-file generation with mocked LLM response."""
    from woo_hoo.services.openrouter import ChatCompletionChoice, ChatCompletionResponse, ChatMessage

    mock_xml_response = """<?xml version="1.0" encoding="UTF-8"?>
<diwoo:Document xmlns:diwoo="https://standaarden.overheid.nl/diwoo/metadata/">
  <diwoo:DiWoo>
    <diwoo:identifiers>
      <diwoo:identifier>PUB-2024-001</diwoo:identifier>
    </diwoo:identifiers>
    <diwoo:publisher resource="https://identifier.overheid.nl/tooi/id/gemeente/gm0363">Test Publisher</diwoo:publisher>
    <diwoo:titelcollectie>
      <diwoo:officieleTitel>Publication Test Document</diwoo:officieleTitel>
    </diwoo:titelcollectie>
    <diwoo:classificatiecollectie>
      <diwoo:informatiecategorieen>
        <diwoo:informatiecategorie resource="https://identifier.overheid.nl/tooi/def/thes/kern/c_5ba23c01">Adviezen</diwoo:informatiecategorie>
      </diwoo:informatiecategorieen>
      <diwoo:trefwoorden>
        <diwoo:trefwoord>test</diwoo:trefwoord>
        <diwoo:trefwoord>publication</diwoo:trefwoord>
      </diwoo:trefwoorden>
    </diwoo:classificatiecollectie>
    <diwoo:documenthandelingen>
      <diwoo:documenthandeling>
        <diwoo:soortHandeling resource="https://identifier.overheid.nl/tooi/def/thes/kern/c_vaststelling">vaststelling</diwoo:soortHandeling>
        <diwoo:atTime>2024-01-15T10:00:00</diwoo:atTime>
      </diwoo:documenthandeling>
    </diwoo:documenthandelingen>
  </diwoo:DiWoo>
</diwoo:Document>"""

    mock_llm_response = ChatCompletionResponse(
        id="test-id",
        model="mistralai/mistral-large-2411",
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=mock_xml_response),
                finish_reason="stop",
            )
        ],
    )

    files = [
        ("files", ("doc1.txt", b"First document content " * 50, "text/plain")),
        ("files", ("doc2.txt", b"Second document content " * 50, "text/plain")),
    ]

    with patch("woo_hoo.services.metadata_generator.MetadataGenerator._get_client") as mock_get_llm:
        mock_llm_client = AsyncMock()
        mock_llm_client.chat_completion = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm_client

        response = await async_client.post(
            "/api/v1/metadata/generate-for-publication",
            files=files,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["documents_processed"] == 2
    assert data["documents_failed"] == 0
    assert "suggestion" in data
    assert data["suggestion"]["publication_metadata"]["titelcollectie"]["officieleTitel"] == "Publication Test Document"
    assert "overall_confidence" in data["suggestion"]
    assert len(data["suggestion"]["document_suggestions"]) == 2
    assert "aggregated_keywords" in data["suggestion"]


# Tests for publication UUID-based metadata generation endpoint


@pytest.mark.asyncio
async def test_generate_from_publication_publicatiebank_not_configured(async_client: AsyncClient):
    """Should return error when publicatiebank is not configured."""
    response = await async_client.post(
        "/api/v1/metadata/generate-from-publication/550e8400-e29b-41d4-a716-446655440000",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "GPP_PUBLICATIEBANK_URL" in data["error"]


@pytest.mark.asyncio
async def test_generate_from_publication_not_found(async_client: AsyncClient):
    """Should return error when publication is not found."""
    from woo_hoo.services.publicatiebank_client import PublicationNotFoundError

    with patch("woo_hoo.api.routers.metadata.PublicatiebankClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.is_configured = True
        mock_instance.get_publication_with_documents = AsyncMock(
            side_effect=PublicationNotFoundError("Publication not found")
        )
        mock_instance.close = AsyncMock()
        MockClient.return_value = mock_instance

        response = await async_client.post(
            "/api/v1/metadata/generate-from-publication/550e8400-e29b-41d4-a716-446655440000",
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "not found" in data["error"].lower()


@pytest.mark.asyncio
async def test_generate_from_publication_no_documents(async_client: AsyncClient):
    """Should return error when publication has no documents."""
    from woo_hoo.services.publicatiebank_client import PublicatiebankPublication

    mock_publication = PublicatiebankPublication(
        uuid="550e8400-e29b-41d4-a716-446655440000",
        officiele_titel="Test Publication",
        verkorte_titel="Test",
        omschrijving="A test publication",
        publicatiestatus="concept",
        publisher="Test Publisher",
        informatie_categorieen=["adviezen"],
        onderwerpen=[],
        kenmerken=[],
        documents=[],
    )

    with patch("woo_hoo.api.routers.metadata.PublicatiebankClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.is_configured = True
        mock_instance.get_publication_with_documents = AsyncMock(return_value=mock_publication)
        mock_instance.close = AsyncMock()
        MockClient.return_value = mock_instance

        response = await async_client.post(
            "/api/v1/metadata/generate-from-publication/550e8400-e29b-41d4-a716-446655440000",
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "no downloadable documents" in data["error"].lower()


@pytest.mark.asyncio
async def test_generate_from_publication_with_mock(async_client: AsyncClient):
    """Test successful generation from publication with mocked responses."""
    from woo_hoo.services.openrouter import ChatCompletionChoice, ChatCompletionResponse, ChatMessage
    from woo_hoo.services.publicatiebank_client import PublicatiebankDocument, PublicatiebankPublication

    mock_documents = [
        PublicatiebankDocument(
            uuid="doc-uuid-1",
            officiele_titel="Document 1",
            verkorte_titel="Doc 1",
            omschrijving="First document",
            bestandsnaam="doc1.txt",
            bestandsformaat="text/plain",
            bestandsomvang=1024,
            publicatiestatus="published",
            content=b"Document one content " * 50,
            kenmerken=[],
        ),
        PublicatiebankDocument(
            uuid="doc-uuid-2",
            officiele_titel="Document 2",
            verkorte_titel="Doc 2",
            omschrijving="Second document",
            bestandsnaam="doc2.txt",
            bestandsformaat="text/plain",
            bestandsomvang=1024,
            publicatiestatus="published",
            content=b"Document two content " * 50,
            kenmerken=[],
        ),
    ]

    mock_publication = PublicatiebankPublication(
        uuid="550e8400-e29b-41d4-a716-446655440000",
        officiele_titel="Test Publication",
        verkorte_titel="Test",
        omschrijving="A test publication with documents",
        publicatiestatus="concept",
        publisher="Test Publisher",
        informatie_categorieen=["adviezen"],
        onderwerpen=[],
        kenmerken=[],
        documents=mock_documents,
    )

    mock_xml_response = """<?xml version="1.0" encoding="UTF-8"?>
<diwoo:Document xmlns:diwoo="https://standaarden.overheid.nl/diwoo/metadata/">
  <diwoo:DiWoo>
    <diwoo:identifiers>
      <diwoo:identifier>PUB-2024-001</diwoo:identifier>
    </diwoo:identifiers>
    <diwoo:publisher resource="https://identifier.overheid.nl/tooi/id/gemeente/gm0363">Test Publisher</diwoo:publisher>
    <diwoo:titelcollectie>
      <diwoo:officieleTitel>Generated Publication Title</diwoo:officieleTitel>
    </diwoo:titelcollectie>
    <diwoo:classificatiecollectie>
      <diwoo:informatiecategorieen>
        <diwoo:informatiecategorie resource="https://identifier.overheid.nl/tooi/def/thes/kern/c_5ba23c01">Adviezen</diwoo:informatiecategorie>
      </diwoo:informatiecategorieen>
      <diwoo:trefwoorden>
        <diwoo:trefwoord>generated</diwoo:trefwoord>
        <diwoo:trefwoord>metadata</diwoo:trefwoord>
      </diwoo:trefwoorden>
    </diwoo:classificatiecollectie>
    <diwoo:documenthandelingen>
      <diwoo:documenthandeling>
        <diwoo:soortHandeling resource="https://identifier.overheid.nl/tooi/def/thes/kern/c_vaststelling">vaststelling</diwoo:soortHandeling>
        <diwoo:atTime>2024-01-15T10:00:00</diwoo:atTime>
      </diwoo:documenthandeling>
    </diwoo:documenthandelingen>
  </diwoo:DiWoo>
</diwoo:Document>"""

    mock_llm_response = ChatCompletionResponse(
        id="test-id",
        model="mistralai/mistral-large-2411",
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=mock_xml_response),
                finish_reason="stop",
            )
        ],
    )

    with (
        patch("woo_hoo.api.routers.metadata.PublicatiebankClient") as MockPubClient,
        patch("woo_hoo.services.metadata_generator.MetadataGenerator._get_client") as mock_get_llm,
    ):
        mock_pub_instance = AsyncMock()
        mock_pub_instance.is_configured = True
        mock_pub_instance.get_publication_with_documents = AsyncMock(return_value=mock_publication)
        mock_pub_instance.close = AsyncMock()
        MockPubClient.return_value = mock_pub_instance

        mock_llm_client = AsyncMock()
        mock_llm_client.chat_completion = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm_client

        response = await async_client.post(
            "/api/v1/metadata/generate-from-publication/550e8400-e29b-41d4-a716-446655440000",
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["documents_processed"] == 2
    assert data["documents_failed"] == 0
    assert "suggestion" in data
    assert data["suggestion"]["publication_metadata"]["titelcollectie"]["officieleTitel"] == "Generated Publication Title"
    assert "overall_confidence" in data["suggestion"]
    assert data["suggestion"]["overall_confidence"]["overall"] > 0
    assert len(data["suggestion"]["document_suggestions"]) == 2
    # Verify document UUIDs are preserved
    doc_uuids = [doc["document_uuid"] for doc in data["suggestion"]["document_suggestions"]]
    assert "doc-uuid-1" in doc_uuids
    assert "doc-uuid-2" in doc_uuids


class TestOpenAPISchema:
    """Tests for OpenAPI schema availability."""

    @pytest.mark.asyncio
    async def test_openapi_schema_available(self, async_client: AsyncClient):
        """OpenAPI schema should be accessible."""
        response = await async_client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "woo-hoo"
        assert "paths" in data

    @pytest.mark.asyncio
    async def test_swagger_docs_available(self, async_client: AsyncClient):
        """Swagger UI should be accessible."""
        response = await async_client.get("/docs")

        assert response.status_code == 200
        assert (
            "swagger" in response.text.lower()
            or "redoc" in response.text.lower()
            or "html" in response.headers.get("content-type", "")
        )
