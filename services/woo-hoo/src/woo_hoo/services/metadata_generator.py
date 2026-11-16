"""Core metadata generation service.

Orchestrates LLM-based DIWOO metadata extraction from document content.
Supports both JSON and XML output modes.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import date, datetime

from pydantic import HttpUrl, ValidationError

from woo_hoo.config import Settings, get_settings
from woo_hoo.models.diwoo import (
    ClassificatieCollectie,
    DiWooMetadata,
    DocumentHandeling,
    DocumentRelatieItem,
    DocumentRelatieMeta,
    DocumentSoortMeta,
    DocumentVerwijzing,
    Geldigheid,
    InformatieCategorieMeta,
    Organisatie,
    SoortHandelingMeta,
    TaalMeta,
    TitelCollectie,
)
from woo_hoo.models.enums import DocumentRelatie, DocumentSoort, InformatieCategorie, SoortHandeling, Taal
from woo_hoo.models.requests import MetadataGenerationRequest, PublisherHint
from woo_hoo.models.responses import (
    ConfidenceScores,
    FieldConfidence,
    MetadataGenerationResponse,
    MetadataSuggestion,
)
from woo_hoo.services.openrouter import ChatMessage, OpenRouterClient
from woo_hoo.services.prompt_templates import OutputMode, build_extraction_prompt, get_system_prompt
from woo_hoo.services.xml_parser import XMLParseError, XMLValidationError, parse_xml_to_diwoo
from woo_hoo.utils.logging import get_logger

logger = get_logger(__name__)


class MetadataGenerationError(Exception):
    """Raised when metadata generation fails."""

    pass


class MetadataGenerator:
    """Service for generating DIWOO-compliant metadata using LLMs."""

    def __init__(
        self,
        client: OpenRouterClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize the generator.

        Args:
            client: OpenRouter client (creates one if not provided)
            settings: Application settings (uses get_settings() if not provided)
        """
        self.settings = settings or get_settings()
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> OpenRouterClient:
        """Get or create the OpenRouter client."""
        if self._client is None:
            self._client = OpenRouterClient(self.settings)
        return self._client

    async def generate(
        self,
        request: MetadataGenerationRequest,
        output_mode: OutputMode = OutputMode.XML,
        validate_xml: bool = False,
    ) -> MetadataGenerationResponse:
        """Generate DIWOO metadata for a document.

        Args:
            request: Metadata generation request with document content
            output_mode: Whether to use XML (default) or JSON output from LLM
            validate_xml: Whether to validate XML against XSD schema (only for XML mode)

        Returns:
            Response with generated metadata or error
        """
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        logger.info(
            "Starting metadata generation",
            request_id=request_id,
            text_length=len(request.document.text),
            has_publisher_hint=request.publisher_hint is not None,
            output_mode=output_mode.value,
        )

        try:
            client = await self._get_client()

            # Build prompt
            publisher_name = request.publisher_hint.name if request.publisher_hint else None
            prompt = build_extraction_prompt(
                document_text=request.document.text,
                publisher_hint=publisher_name,
                max_text_length=self.settings.max_text_length,
                output_mode=output_mode,
            )

            messages = [
                ChatMessage(role="system", content=get_system_prompt(output_mode=output_mode)),
                ChatMessage(role="user", content=prompt),
            ]

            # Call LLM - only use json_object format for JSON mode
            model = request.model
            response_format = {"type": "json_object"} if output_mode == OutputMode.JSON else None
            response = await client.chat_completion(
                messages=messages,
                model=model,
                temperature=self.settings.llm_temperature,
                response_format=response_format,
            )

            # Parse LLM response
            raw_content = response.choices[0].message.content

            if output_mode == OutputMode.XML:
                # Parse XML and convert to DIWOO metadata
                metadata = parse_xml_to_diwoo(raw_content, validate=validate_xml)
                # XML mode doesn't have confidence scores
                confidence = ConfidenceScores(overall=0.8, fields=[])
            else:
                # Parse JSON and transform to DIWOO structure
                llm_output = json.loads(raw_content)
                metadata = self._transform_to_diwoo(llm_output, request.publisher_hint)
                confidence = (
                    self._extract_confidence(llm_output)
                    if request.include_confidence
                    else ConfidenceScores(overall=0.7, fields=[])
                )

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            suggestion = MetadataSuggestion(
                metadata=metadata,
                confidence=confidence,
                model_used=model,
                processing_time_ms=elapsed_ms,
            )

            logger.info(
                "Metadata generation completed",
                request_id=request_id,
                elapsed_ms=elapsed_ms,
                overall_confidence=confidence.overall,
                output_mode=output_mode.value,
            )

            return MetadataGenerationResponse(
                success=True,
                request_id=request_id,
                suggestion=suggestion,
            )

        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM JSON response", request_id=request_id, error=str(e))
            return MetadataGenerationResponse(
                success=False,
                request_id=request_id,
                error=f"LLM returned invalid JSON: {e}",
            )

        except (XMLParseError, XMLValidationError) as e:
            logger.error("Failed to parse LLM XML response", request_id=request_id, error=str(e))
            return MetadataGenerationResponse(
                success=False,
                request_id=request_id,
                error=f"LLM returned invalid XML: {e}",
            )

        except ValidationError as e:
            logger.error("Metadata validation failed", request_id=request_id, error=str(e))
            return MetadataGenerationResponse(
                success=False,
                request_id=request_id,
                error=f"Generated metadata validation failed: {e}",
            )

        except Exception as e:
            logger.exception("Metadata generation failed", request_id=request_id)
            return MetadataGenerationResponse(
                success=False,
                request_id=request_id,
                error=str(e),
            )

    def _transform_to_diwoo(
        self,
        llm_output: dict,
        publisher_hint: PublisherHint | None,
    ) -> DiWooMetadata:
        """Transform LLM output to DIWOO metadata structure.

        Args:
            llm_output: Parsed JSON from LLM
            publisher_hint: Optional publisher information

        Returns:
            DiWooMetadata instance
        """
        # Build publisher - prefer LLM extraction, fall back to hint
        publisher = self._extract_organisation(llm_output.get("publisher"), publisher_hint)

        # Extract other organisations
        verantwoordelijke = self._extract_organisation(llm_output.get("verantwoordelijke"))
        opsteller = self._extract_organisation(llm_output.get("opsteller"))

        # Build titel collectie
        titel_data = llm_output.get("titelcollectie", {})
        if isinstance(titel_data, dict):
            officiele_titel = titel_data.get("officieleTitel") or titel_data.get("officiele_titel", "Onbekende titel")
            verkorte_titels = titel_data.get("verkorteTitels") or titel_data.get("verkorte_titels")
            alternatieve_titels = titel_data.get("alternatieveTitels") or titel_data.get("alternatieve_titels")
        else:
            # Fallback for old format
            officiele_titel = llm_output.get("officiele_titel", "Onbekende titel")
            verkorte_titels = llm_output.get("verkorte_titels")
            alternatieve_titels = None

        titelcollectie = TitelCollectie(
            officiele_titel=officiele_titel[:2000],
            verkorte_titels=verkorte_titels,
            alternatieve_titels=alternatieve_titels,
        )

        # Build informatiecategorieen - handle nested structure
        classificatie_data = llm_output.get("classificatiecollectie", {})
        if isinstance(classificatie_data, dict):
            raw_categories = classificatie_data.get("informatiecategorieen", [])
            raw_soorten = classificatie_data.get("documentsoorten")
            trefwoorden = classificatie_data.get("trefwoorden")
        else:
            # Fallback for old format
            raw_categories = llm_output.get("informatiecategorieen", [])
            raw_soorten = llm_output.get("documentsoorten")
            trefwoorden = llm_output.get("trefwoorden")

        informatiecategorieen: list[InformatieCategorieMeta] = []
        for cat_data in raw_categories:
            cat_name = cat_data.get("categorie", "").upper().replace(" ", "_")
            try:
                cat_enum = InformatieCategorie[cat_name]
                informatiecategorieen.append(InformatieCategorieMeta(categorie=cat_enum))
            except KeyError:
                logger.warning("Unknown informatiecategorie from LLM", categorie=cat_name)

        # Ensure at least one category
        if not informatiecategorieen:
            informatiecategorieen = [InformatieCategorieMeta(categorie=InformatieCategorie.OVERIGE_BESLUITEN_AS)]

        # Build documentsoorten
        documentsoorten: list[DocumentSoortMeta] | None = None
        if raw_soorten:
            documentsoorten = []
            for soort_name in raw_soorten:
                try:
                    soort_enum = DocumentSoort[soort_name.upper().replace(" ", "_")]
                    documentsoorten.append(DocumentSoortMeta(soort=soort_enum))
                except KeyError:
                    logger.warning("Unknown documentsoort from LLM", soort=soort_name)

        # Build classificatie collectie
        classificatiecollectie = ClassificatieCollectie(
            informatiecategorieen=informatiecategorieen,
            documentsoorten=documentsoorten if documentsoorten else None,
            trefwoorden=trefwoorden,
        )

        # Build document handeling
        documenthandelingen = [
            DocumentHandeling(
                soort_handeling=SoortHandelingMeta(handeling=SoortHandeling.REGISTRATIE),
                at_time=datetime.now(),
                was_associated_with=publisher,
            )
        ]

        # Parse creatiedatum
        creatiedatum: date | None = None
        raw_date = llm_output.get("creatiedatum")
        if raw_date:
            try:
                creatiedatum = date.fromisoformat(raw_date)
            except ValueError:
                logger.warning("Could not parse creatiedatum", value=raw_date)

        # Parse geldigheid
        geldigheid = self._extract_geldigheid(llm_output.get("geldigheid"))

        # Build document relations
        documentrelaties = self._extract_documentrelaties(llm_output.get("documentrelaties"))

        # Build language
        taal_str = llm_output.get("taal", "NL").upper()
        try:
            taal_enum = Taal[taal_str]
        except KeyError:
            taal_enum = Taal.NL
        language = TaalMeta(taal=taal_enum)

        # Extract identifiers
        identifiers = llm_output.get("identifiers")
        if identifiers and not isinstance(identifiers, list):
            identifiers = [identifiers]

        # Extract omschrijvingen
        omschrijvingen = llm_output.get("omschrijvingen")
        if omschrijvingen and not isinstance(omschrijvingen, list):
            omschrijvingen = [omschrijvingen]

        # Extract naamOpsteller (LLM may return list, join if needed)
        naam_opsteller = llm_output.get("naamOpsteller")
        if isinstance(naam_opsteller, list):
            naam_opsteller = ", ".join(naam_opsteller)

        return DiWooMetadata(
            identifiers=identifiers,
            publisher=publisher,
            verantwoordelijke=verantwoordelijke,
            opsteller=opsteller,
            naam_opsteller=naam_opsteller,
            titelcollectie=titelcollectie,
            classificatiecollectie=classificatiecollectie,
            documenthandelingen=documenthandelingen,
            omschrijvingen=omschrijvingen,
            creatiedatum=creatiedatum,
            geldigheid=geldigheid,
            aggregatiekenmerk=llm_output.get("aggregatiekenmerk"),
            documentrelaties=documentrelaties,
            language=language,
        )

    def _extract_organisation(
        self,
        llm_data: dict | None,
        hint: PublisherHint | None = None,
    ) -> Organisatie:
        """Extract organisation from LLM output or hint.

        Args:
            llm_data: Organisation data from LLM (name, type)
            hint: Optional publisher hint fallback

        Returns:
            Organisatie instance
        """
        # Try to use LLM-extracted data first
        if llm_data and isinstance(llm_data, dict):
            name = llm_data.get("name")
            if name:
                # Build placeholder URI based on type
                org_type = llm_data.get("type", "organisatie")
                uri = f"https://identifier.overheid.nl/tooi/id/{org_type}/placeholder"
                return Organisatie(resource=HttpUrl(uri), label=name)

        # Fall back to hint
        if hint:
            return Organisatie(
                resource=hint.tooi_uri or HttpUrl("https://identifier.overheid.nl/tooi/id/organisatie/placeholder"),
                label=hint.name,
            )

        # Default placeholder
        return Organisatie(
            resource=HttpUrl("https://identifier.overheid.nl/tooi/id/organisatie/placeholder"),
            label="Onbekende organisatie",
        )

    def _extract_geldigheid(self, llm_data: dict | None) -> Geldigheid | None:
        """Extract validity period from LLM output.

        Args:
            llm_data: Geldigheid data with begindatum/einddatum

        Returns:
            Geldigheid instance or None
        """
        if not llm_data or not isinstance(llm_data, dict):
            return None

        begindatum = None
        einddatum = None

        raw_begin = llm_data.get("begindatum")
        if raw_begin:
            try:
                begindatum = datetime.fromisoformat(raw_begin)
            except ValueError:
                logger.warning("Could not parse geldigheid begindatum", value=raw_begin)

        raw_eind = llm_data.get("einddatum")
        if raw_eind:
            try:
                einddatum = datetime.fromisoformat(raw_eind)
            except ValueError:
                logger.warning("Could not parse geldigheid einddatum", value=raw_eind)

        if begindatum or einddatum:
            return Geldigheid(begindatum=begindatum, einddatum=einddatum)
        return None

    def _extract_documentrelaties(self, llm_data: list | None) -> list[DocumentRelatieItem] | None:
        """Extract document relations from LLM output.

        Args:
            llm_data: List of relation dicts with type and label

        Returns:
            List of DocumentRelatieItem or None
        """
        if not llm_data or not isinstance(llm_data, list):
            return None

        # Map LLM relation types to DocumentRelatie enum
        type_mapping = {
            "BIJLAGE": DocumentRelatie.HEEFT_BIJLAGE,
            "HEEFT_BIJLAGE": DocumentRelatie.HEEFT_BIJLAGE,
            "IS_BIJLAGE_VAN": DocumentRelatie.IS_BIJLAGE_VAN,
            "VERWIJZING": DocumentRelatie.HEEFT_BIJLAGE,  # Closest match
            "REACTIE_OP": DocumentRelatie.WIJZIGT,  # Closest match
            "VERVANGT": DocumentRelatie.VERVANGT,
            "WIJZIGT": DocumentRelatie.WIJZIGT,
        }

        relations: list[DocumentRelatieItem] = []
        for rel_data in llm_data:
            if not isinstance(rel_data, dict):
                continue

            rel_type = rel_data.get("type", "").upper()
            label = rel_data.get("label", "")

            if not label:
                continue

            # Map to enum
            relatie_enum = type_mapping.get(rel_type, DocumentRelatie.HEEFT_BIJLAGE)

            relations.append(
                DocumentRelatieItem(
                    role=DocumentRelatieMeta(relatie=relatie_enum),
                    relation=DocumentVerwijzing(label=label),
                )
            )

        return relations if relations else None

    def _extract_confidence(self, llm_output: dict) -> ConfidenceScores:
        """Extract confidence scores from LLM output.

        Args:
            llm_output: Parsed JSON from LLM

        Returns:
            ConfidenceScores instance
        """
        raw_scores = llm_output.get("confidence_scores", {})
        overall = raw_scores.get("overall", 0.7)

        fields: list[FieldConfidence] = []
        for field_name, score in raw_scores.items():
            if field_name != "overall" and isinstance(score, (int, float)):
                fields.append(FieldConfidence(field_name=field_name, confidence=float(score)))

        # Add reasoning from informatiecategorieen
        for cat_data in llm_output.get("informatiecategorieen", []):
            if "reasoning" in cat_data:
                fields.append(
                    FieldConfidence(
                        field_name=f"informatiecategorie_{cat_data.get('categorie', 'unknown')}",
                        confidence=cat_data.get("confidence", 0.7),
                        reasoning=cat_data.get("reasoning"),
                    )
                )

        return ConfidenceScores(overall=overall, fields=fields)

    async def close(self) -> None:
        """Close the OpenRouter client if we own it."""
        if self._owns_client and self._client:
            await self._client.close()
