"""XML parser for DIWOO metadata with XSD validation.

Parses XML output from LLM and converts to Pydantic models.
"""

from __future__ import annotations

import contextlib
import re
from datetime import date, datetime
from pathlib import Path

from lxml import etree
from pydantic import HttpUrl

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
from woo_hoo.utils.logging import get_logger

logger = get_logger(__name__)

# DIWOO namespace
DIWOO_NS = "https://standaarden.overheid.nl/diwoo/metadata/"
NAMESPACES = {"diwoo": DIWOO_NS}

# Path to XSD schemas
SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"


class XMLParseError(Exception):
    """Raised when XML parsing fails."""

    pass


class XMLValidationError(Exception):
    """Raised when XML validation against XSD fails."""

    pass


def _get_text(element: etree._Element | None) -> str | None:
    """Get text content from element, stripping whitespace."""
    if element is None:
        return None
    text = element.text
    return text.strip() if text else None


def _get_attr(element: etree._Element | None, attr: str) -> str | None:
    """Get attribute value from element."""
    if element is None:
        return None
    return element.get(attr)


def _find(parent: etree._Element, path: str) -> etree._Element | None:
    """Find element using XPath with namespace."""
    return parent.find(path, namespaces=NAMESPACES)


def _findall(parent: etree._Element, path: str) -> list[etree._Element]:
    """Find all elements using XPath with namespace."""
    return parent.findall(path, namespaces=NAMESPACES)


def _parse_date(value: str | None) -> date | None:
    """Parse ISO date string to date object."""
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])  # Handle datetime strings
    except ValueError:
        logger.warning("Could not parse date", value=value)
        return None


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string to datetime object."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("Could not parse datetime", value=value)
        return None


def _extract_category_code(resource: str | None) -> str | None:
    """Extract category code from TOOI URI."""
    if not resource:
        return None
    # Extract last part of URI like c_4edc7ff0 or c_woo_besluit
    match = re.search(r"(c_[a-z0-9_]+)$", resource)
    return match.group(1) if match else None


def load_xsd_schema() -> etree.XMLSchema | None:
    """Load the DIWOO XSD schema for validation.

    Returns:
        XMLSchema object or None if schemas not available
    """
    xsd_path = SCHEMAS_DIR / "diwoo-metadata.xsd"
    if not xsd_path.exists():
        logger.warning("XSD schema not found", path=str(xsd_path))
        return None

    try:
        with open(xsd_path, "rb") as f:
            schema_doc = etree.parse(f)
        return etree.XMLSchema(schema_doc)
    except Exception as e:
        logger.warning("Failed to load XSD schema", error=str(e))
        return None


def clean_xml_response(raw_xml: str) -> str:
    """Clean XML response from LLM.

    Removes markdown code blocks and other noise.

    Args:
        raw_xml: Raw XML string from LLM

    Returns:
        Cleaned XML string
    """
    # Remove markdown code blocks
    cleaned = re.sub(r"```xml\s*", "", raw_xml)
    cleaned = re.sub(r"```\s*", "", cleaned)

    # Find the XML declaration or root element
    xml_match = re.search(r"(<\?xml.*?\?>)?\s*(<diwoo:Document.*</diwoo:Document>)", cleaned, re.DOTALL)
    if xml_match:
        declaration = xml_match.group(1) or '<?xml version="1.0" encoding="UTF-8"?>'
        body = xml_match.group(2)
        return f"{declaration}\n{body}"

    # Try to find just the Document element
    doc_match = re.search(r"<diwoo:Document.*</diwoo:Document>", cleaned, re.DOTALL)
    if doc_match:
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{doc_match.group(0)}'

    return cleaned.strip()


def parse_xml_to_diwoo(
    xml_string: str,
    validate: bool = False,
) -> DiWooMetadata:
    """Parse XML string to DiWooMetadata.

    Args:
        xml_string: XML string from LLM
        validate: Whether to validate against XSD schema

    Returns:
        DiWooMetadata instance

    Raises:
        XMLParseError: If XML is malformed
        XMLValidationError: If validation fails
    """
    # Clean the XML
    cleaned_xml = clean_xml_response(xml_string)

    # Parse XML
    try:
        root = etree.fromstring(cleaned_xml.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        raise XMLParseError(f"Invalid XML: {e}") from e

    # Validate against XSD if requested
    if validate:
        schema = load_xsd_schema()
        if schema and not schema.validate(root):
            errors = [str(err) for err in schema.error_log]
            raise XMLValidationError(f"XSD validation failed: {errors}")

    # Find DiWoo element
    diwoo = _find(root, "diwoo:DiWoo")
    if diwoo is None:
        raise XMLParseError("Missing diwoo:DiWoo element")

    # Extract identifiers
    identifiers = None
    identifiers_elem = _find(diwoo, "diwoo:identifiers")
    if identifiers_elem is not None:
        identifiers = [_get_text(elem) for elem in _findall(identifiers_elem, "diwoo:identifier") if _get_text(elem)]

    # Extract publisher
    publisher = _parse_organisation(_find(diwoo, "diwoo:publisher"))

    # Extract other organisations
    verantwoordelijke = _parse_organisation(_find(diwoo, "diwoo:verantwoordelijke"))
    opsteller = _parse_organisation(_find(diwoo, "diwoo:opsteller"))

    # Extract naamOpsteller
    naam_opsteller = _get_text(_find(diwoo, "diwoo:naamOpsteller"))

    # Extract titelcollectie
    titelcollectie = _parse_titelcollectie(_find(diwoo, "diwoo:titelcollectie"))

    # Extract omschrijvingen
    omschrijvingen = None
    omschrijvingen_elem = _find(diwoo, "diwoo:omschrijvingen")
    if omschrijvingen_elem is not None:
        omschrijvingen = [
            _get_text(elem) for elem in _findall(omschrijvingen_elem, "diwoo:omschrijving") if _get_text(elem)
        ]

    # Extract classificatiecollectie
    classificatiecollectie = _parse_classificatiecollectie(_find(diwoo, "diwoo:classificatiecollectie"))

    # Extract creatiedatum
    creatiedatum = _parse_date(_get_text(_find(diwoo, "diwoo:creatiedatum")))

    # Extract geldigheid
    geldigheid = _parse_geldigheid(_find(diwoo, "diwoo:geldigheid"))

    # Extract language
    language = _parse_language(_find(diwoo, "diwoo:language"))

    # Extract aggregatiekenmerk
    aggregatiekenmerk = _get_text(_find(diwoo, "diwoo:aggregatiekenmerk"))

    # Extract documenthandelingen
    documenthandelingen = _parse_documenthandelingen(_find(diwoo, "diwoo:documenthandelingen"), publisher)

    # Extract documentrelaties
    documentrelaties = _parse_documentrelaties(_find(diwoo, "diwoo:documentrelaties"))

    return DiWooMetadata(
        identifiers=identifiers,
        publisher=publisher,
        verantwoordelijke=verantwoordelijke,
        opsteller=opsteller,
        naam_opsteller=naam_opsteller,
        titelcollectie=titelcollectie,
        omschrijvingen=omschrijvingen,
        classificatiecollectie=classificatiecollectie,
        creatiedatum=creatiedatum,
        geldigheid=geldigheid,
        aggregatiekenmerk=aggregatiekenmerk,
        documenthandelingen=documenthandelingen,
        documentrelaties=documentrelaties,
        language=language,
    )


def _parse_organisation(elem: etree._Element | None) -> Organisatie:
    """Parse organisation element."""
    if elem is None:
        return Organisatie(
            resource=HttpUrl("https://identifier.overheid.nl/tooi/id/organisatie/placeholder"),
            label="Onbekende organisatie",
        )

    resource = _get_attr(elem, "resource")
    label = _get_text(elem) or "Onbekende organisatie"

    if resource:
        return Organisatie(resource=HttpUrl(resource), label=label)
    else:
        return Organisatie(
            resource=HttpUrl("https://identifier.overheid.nl/tooi/id/organisatie/placeholder"),
            label=label,
        )


def _parse_titelcollectie(elem: etree._Element | None) -> TitelCollectie:
    """Parse titelcollectie element."""
    if elem is None:
        return TitelCollectie(officiele_titel="Onbekende titel")

    officiele_titel = _get_text(_find(elem, "diwoo:officieleTitel")) or "Onbekende titel"

    verkorte_titels = [_get_text(e) for e in _findall(elem, "diwoo:verkorteTitel") if _get_text(e)]
    alternatieve_titels = [_get_text(e) for e in _findall(elem, "diwoo:alternatieveTitel") if _get_text(e)]

    return TitelCollectie(
        officiele_titel=officiele_titel[:2000],
        verkorte_titels=verkorte_titels if verkorte_titels else None,
        alternatieve_titels=alternatieve_titels if alternatieve_titels else None,
    )


def _parse_classificatiecollectie(elem: etree._Element | None) -> ClassificatieCollectie:
    """Parse classificatiecollectie element."""
    if elem is None:
        return ClassificatieCollectie(
            informatiecategorieen=[InformatieCategorieMeta(categorie=InformatieCategorie.OVERIGE_BESLUITEN_AS)]
        )

    # Parse informatiecategorieen
    informatiecategorieen: list[InformatieCategorieMeta] = []
    info_elem = _find(elem, "diwoo:informatiecategorieen")
    if info_elem is not None:
        for cat_elem in _findall(info_elem, "diwoo:informatiecategorie"):
            resource = _get_attr(cat_elem, "resource")
            code = _extract_category_code(resource)
            if code:
                try:
                    cat_enum = InformatieCategorie(code)
                    informatiecategorieen.append(InformatieCategorieMeta(categorie=cat_enum))
                except ValueError:
                    logger.warning("Unknown informatiecategorie", code=code)

    if not informatiecategorieen:
        informatiecategorieen = [InformatieCategorieMeta(categorie=InformatieCategorie.OVERIGE_BESLUITEN_AS)]

    # Parse documentsoorten
    documentsoorten: list[DocumentSoortMeta] | None = None
    soorten_elem = _find(elem, "diwoo:documentsoorten")
    if soorten_elem is not None:
        documentsoorten = []
        for soort_elem in _findall(soorten_elem, "diwoo:documentsoort"):
            resource = _get_attr(soort_elem, "resource")
            code = _extract_category_code(resource)
            if code:
                try:
                    soort_enum = DocumentSoort(code)
                    documentsoorten.append(DocumentSoortMeta(soort=soort_enum))
                except ValueError:
                    logger.warning("Unknown documentsoort", code=code)

    # Parse trefwoorden
    trefwoorden: list[str] | None = None
    tref_elem = _find(elem, "diwoo:trefwoorden")
    if tref_elem is not None:
        trefwoorden = [_get_text(e) for e in _findall(tref_elem, "diwoo:trefwoord") if _get_text(e)]

    return ClassificatieCollectie(
        informatiecategorieen=informatiecategorieen,
        documentsoorten=documentsoorten if documentsoorten else None,
        trefwoorden=trefwoorden if trefwoorden else None,
    )


def _parse_geldigheid(elem: etree._Element | None) -> Geldigheid | None:
    """Parse geldigheid element."""
    if elem is None:
        return None

    begindatum = _parse_datetime(_get_text(_find(elem, "diwoo:begindatum")))
    einddatum = _parse_datetime(_get_text(_find(elem, "diwoo:einddatum")))

    if begindatum or einddatum:
        return Geldigheid(begindatum=begindatum, einddatum=einddatum)
    return None


def _parse_language(elem: etree._Element | None) -> TaalMeta | None:
    """Parse language element."""
    if elem is None:
        return TaalMeta(taal=Taal.NL)

    resource = _get_attr(elem, "resource")
    if resource:
        code = _extract_category_code(resource)
        if code:
            try:
                return TaalMeta(taal=Taal(code))
            except ValueError:
                pass

    return TaalMeta(taal=Taal.NL)


def _parse_documenthandelingen(
    elem: etree._Element | None,
    publisher: Organisatie,
) -> list[DocumentHandeling]:
    """Parse documenthandelingen element."""
    handelingen: list[DocumentHandeling] = []

    if elem is not None:
        for handeling_elem in _findall(elem, "diwoo:documenthandeling"):
            soort_elem = _find(handeling_elem, "diwoo:soortHandeling")
            at_time_str = _get_text(_find(handeling_elem, "diwoo:atTime"))
            associated_with = _parse_organisation(_find(handeling_elem, "diwoo:wasAssociatedWith"))

            # Parse soortHandeling
            soort_handeling = SoortHandelingMeta(handeling=SoortHandeling.REGISTRATIE)
            if soort_elem is not None:
                resource = _get_attr(soort_elem, "resource")
                code = _extract_category_code(resource)
                if code:
                    with contextlib.suppress(ValueError):
                        soort_handeling = SoortHandelingMeta(handeling=SoortHandeling(code))

            # Parse atTime
            at_time = _parse_datetime(at_time_str) or datetime.now()

            handelingen.append(
                DocumentHandeling(
                    soort_handeling=soort_handeling,
                    at_time=at_time,
                    was_associated_with=associated_with,
                )
            )

    # Ensure at least one handeling
    if not handelingen:
        handelingen = [
            DocumentHandeling(
                soort_handeling=SoortHandelingMeta(handeling=SoortHandeling.REGISTRATIE),
                at_time=datetime.now(),
                was_associated_with=publisher,
            )
        ]

    return handelingen


def _parse_documentrelaties(elem: etree._Element | None) -> list[DocumentRelatieItem] | None:
    """Parse documentrelaties element."""
    if elem is None:
        return None

    relaties: list[DocumentRelatieItem] = []
    for rel_elem in _findall(elem, "diwoo:documentrelatie"):
        role_elem = _find(rel_elem, "diwoo:role")
        relation_elem = _find(rel_elem, "diwoo:relation")

        if role_elem is None or relation_elem is None:
            continue

        # Parse role
        resource = _get_attr(role_elem, "resource")
        code = _extract_category_code(resource)
        relatie_enum = DocumentRelatie.HEEFT_BIJLAGE
        if code:
            with contextlib.suppress(ValueError):
                relatie_enum = DocumentRelatie(code)

        # Parse relation
        label = _get_text(relation_elem) or "Onbekend document"
        rel_resource = _get_attr(relation_elem, "resource")

        relaties.append(
            DocumentRelatieItem(
                role=DocumentRelatieMeta(relatie=relatie_enum),
                relation=DocumentVerwijzing(resource=rel_resource, label=label),
            )
        )

    return relaties if relaties else None
