"""LLM prompt templates for DIWOO metadata extraction.

Uses instruction files for schema documentation and supports
both structured JSON and XML output modes.
"""

from __future__ import annotations

from enum import Enum
from string import Template

from woo_hoo.models.enums import INFORMATIECATEGORIE_LABELS
from woo_hoo.services.instruction_loader import get_diwoo_schema_instruction, get_diwoo_toml_instruction

# Build category list for prompt
CATEGORY_LIST = "\n".join(
    f"- {cat.name}: {label} (artikel {cat.artikel})" for cat, label in INFORMATIECATEGORIE_LABELS.items()
)


class OutputMode(str, Enum):
    """Output mode for LLM responses."""

    JSON = "json"
    XML = "xml"


def get_system_prompt(include_schema: bool = True, output_mode: OutputMode = OutputMode.JSON) -> str:
    """Get the system prompt for metadata extraction.

    Args:
        include_schema: Whether to include the full DIWOO schema instruction
        output_mode: Whether to output JSON or XML

    Returns:
        System prompt string
    """
    if output_mode == OutputMode.XML:
        base_prompt = """Je bent een expert in Nederlandse overheidsmetadata en de Wet open overheid (Woo).
Je taak is het analyseren van documentinhoud en het genereren van DIWOO-conforme metadata.

BELANGRIJKE REGELS:
1. Antwoord ALLEEN met valid XML - geen markdown codeblocks, geen uitleg
2. Gebruik exact de TOOI resource URIs zoals gespecificeerd
3. Datums in ISO 8601 formaat: YYYY-MM-DD of YYYY-MM-DDTHH:MM:SS
4. Selecteer minimaal één informatiecategorie uit de 17 Woo-categorieën
"""
        if include_schema:
            # Use TOML-based instruction for XML mode
            toml_instruction = get_diwoo_toml_instruction()
            return f"{base_prompt}\n\n{toml_instruction}"
        return base_prompt + f"\n\nDe 17 Woo-informatiecategorieën zijn:\n{CATEGORY_LIST}"

    # Default JSON mode
    base_prompt = """Je bent een expert in Nederlandse overheidsmetadata en de Wet open overheid (Woo).
Je taak is het analyseren van documentinhoud en het genereren van DIWOO-conforme metadata.

BELANGRIJKE REGELS:
1. Antwoord ALLEEN met valid JSON - geen markdown codeblocks, geen uitleg
2. Gebruik exact de categorie-codes zoals gespecificeerd (bijv. WOO_VERZOEKEN, niet "Woo-verzoeken")
3. Datums in ISO 8601 formaat: YYYY-MM-DD
4. Confidence scores tussen 0.0 en 1.0
5. Selecteer minimaal één informatiecategorie uit de 17 Woo-categorieën
"""

    if include_schema:
        schema_instruction = get_diwoo_schema_instruction()
        return f"{base_prompt}\n\n{schema_instruction}"

    return base_prompt + f"\n\nDe 17 Woo-informatiecategorieën zijn:\n{CATEGORY_LIST}"


EXTRACTION_PROMPT_JSON = Template("""Analyseer het volgende document en genereer DIWOO-conforme metadata.

## DOCUMENT
---
$document_text
---
$publisher_hint

## OPDRACHT

Extraheer metadata volgens het DIWOO schema in de systeemprompt.

Belangrijke extractie-instructies:
1. Zoek naar KENMERK, zaaknummer, referentienummers → identifiers
2. Zoek naar organisatie in briefhoofd, handtekening, retouradres → publisher
3. Zoek naar datums in briefhoofd of tekst → creatiedatum
4. Zoek naar onderwerpregel of documenttitel → titelcollectie.officieleTitel
5. Zoek naar namen in handtekeningblok → naamOpsteller
6. Identificeer bijlagen, verwijzingen → documentrelaties

CATEGORIE CODES (gebruik exact deze waarden):
$category_options

Retourneer ALLEEN valid JSON volgens het schema, geen andere tekst.""")


EXTRACTION_PROMPT_XML = Template("""Analyseer het volgende document en genereer DIWOO-conforme metadata als XML.

## DOCUMENT
---
$document_text
---
$publisher_hint

## OPDRACHT

Extraheer metadata en genereer valid XML volgens het DIWOO XSD schema (v0.9.8).

Belangrijke extractie-instructies:
1. Zoek naar KENMERK, zaaknummer, referentienummers → diwoo:identifiers
2. Zoek naar organisatie in briefhoofd, handtekening, retouradres → diwoo:publisher
3. Zoek naar datums in briefhoofd of tekst → diwoo:creatiedatum
4. Zoek naar onderwerpregel of documenttitel → diwoo:officieleTitel
5. Zoek naar namen in handtekeningblok → diwoo:naamOpsteller
6. Identificeer bijlagen, verwijzingen → diwoo:documentrelaties

Retourneer ALLEEN valid XML met de diwoo namespace, geen markdown codeblocks of uitleg.""")


def build_extraction_prompt(
    document_text: str,
    publisher_hint: str | None = None,
    max_text_length: int = 15000,
    output_mode: OutputMode = OutputMode.JSON,
) -> str:
    """Build the extraction prompt with document text.

    Args:
        document_text: Extracted text content from the document
        publisher_hint: Optional hint about the publishing organization
        max_text_length: Maximum text length to include (truncates if longer)
        output_mode: Whether to output JSON or XML

    Returns:
        Formatted prompt string
    """
    # Truncate text if too long
    truncated_text = document_text[:max_text_length]
    if len(document_text) > max_text_length:
        truncated_text += "\n\n[... TEKST AFGEKAPT WEGENS LENGTE ...]"

    # Build publisher hint section
    publisher_section = ""
    if publisher_hint:
        publisher_section = f"\nPUBLISHER HINT: {publisher_hint}\n"

    # Build category options with descriptions
    category_options = "\n".join(f"- {cat.name}: {label}" for cat, label in INFORMATIECATEGORIE_LABELS.items())

    template = EXTRACTION_PROMPT_XML if output_mode == OutputMode.XML else EXTRACTION_PROMPT_JSON

    return template.substitute(
        document_text=truncated_text,
        publisher_hint=publisher_section,
        category_options=category_options,
    )
