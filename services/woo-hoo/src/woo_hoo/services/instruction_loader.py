"""Instruction loader for LLM context shaping.

Loads TOML and markdown instruction files that define the expected output format
for the LLM, ensuring consistent DIWOO-compliant metadata generation.
"""

from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path

from woo_hoo.utils.logging import get_logger

logger = get_logger(__name__)

INSTRUCTIONS_DIR = Path(__file__).parent.parent / "instructions"
SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"


class InstructionNotFoundError(Exception):
    """Raised when an instruction file is not found."""

    pass


@lru_cache(maxsize=16)
def load_instruction(name: str) -> str:
    """Load a markdown instruction file by name.

    Args:
        name: Instruction name (without .md extension)

    Returns:
        Instruction content as string

    Raises:
        InstructionNotFoundError: If instruction file not found
    """
    filepath = INSTRUCTIONS_DIR / f"{name}.md"

    if not filepath.exists():
        available = list_instructions()
        raise InstructionNotFoundError(f"Instruction '{name}' not found. Available: {available}")

    content = filepath.read_text(encoding="utf-8")
    logger.debug("Loaded instruction", name=name, length=len(content))
    return content


@lru_cache(maxsize=16)
def load_toml_config(name: str) -> dict:
    """Load a TOML configuration file by name.

    Args:
        name: Config name (without .toml extension)

    Returns:
        Parsed TOML config as dict

    Raises:
        InstructionNotFoundError: If config file not found
    """
    filepath = INSTRUCTIONS_DIR / f"{name}.toml"

    if not filepath.exists():
        raise InstructionNotFoundError(f"TOML config '{name}' not found at {filepath}")

    content = filepath.read_text(encoding="utf-8")
    config = tomllib.loads(content)
    logger.debug("Loaded TOML config", name=name, keys=list(config.keys()))
    return config


def list_instructions() -> list[str]:
    """List available instruction files (both .md and .toml).

    Returns:
        List of instruction names (without extension)
    """
    if not INSTRUCTIONS_DIR.exists():
        return []

    md_files = [f.stem for f in INSTRUCTIONS_DIR.glob("*.md")]
    toml_files = [f.stem for f in INSTRUCTIONS_DIR.glob("*.toml")]
    return sorted(set(md_files + toml_files))


def get_diwoo_schema_instruction() -> str:
    """Get the DIWOO schema instruction for metadata extraction (JSON mode).

    This is the main instruction used for metadata generation,
    defining the exact JSON output format expected.

    Returns:
        DIWOO schema instruction content
    """
    return load_instruction("diwoo_schema")


def get_diwoo_toml_instruction() -> str:
    """Get the DIWOO instruction from TOML config formatted for LLM.

    Loads the TOML config and formats it into a prompt string.

    Returns:
        Formatted instruction string for LLM
    """
    config = load_toml_config("diwoo_schema")
    return _format_toml_config_to_prompt(config)


def _format_toml_config_to_prompt(config: dict) -> str:
    """Format TOML config into an LLM prompt.

    Args:
        config: Parsed TOML configuration

    Returns:
        Formatted prompt string
    """
    lines = []

    # Metadata section
    meta = config.get("metadata", {})
    lines.append(f"# {meta.get('name', 'DIWOO')} Schema (v{meta.get('version', '0.9.8')})")
    lines.append(f"\n{meta.get('description', '')}\n")

    # Output rules
    rules = config.get("rules", {})
    lines.append("## Output Rules")
    lines.append(f"- {rules.get('response_format', '')}")
    lines.append(f"- Date format: {rules.get('date_format', 'YYYY-MM-DD')}")
    lines.append(f"- Minimum categories: {rules.get('min_categories', 1)}\n")

    # Extraction instructions
    extraction = config.get("extraction", {})
    if extraction:
        lines.append("## Extraction Instructions")
        for field, instruction in extraction.items():
            lines.append(f"- **{field}**: {instruction}")
        lines.append("")

    # Categories
    categories = config.get("categories", {})
    if categories:
        lines.append("## Information Categories (Article 3.3 Woo)")
        lines.append("| Code | Resource URI | Label | Use When |")
        lines.append("|------|-------------|-------|----------|")
        for code, cat in categories.items():
            lines.append(
                f"| {code} | `{cat.get('resource', '')}` | {cat.get('label', '')} | {cat.get('use_when', '')} |"
            )
        lines.append("")

    # Document types
    documentsoorten = config.get("documentsoorten", {})
    if documentsoorten:
        lines.append("## Document Types")
        for code, doc in documentsoorten.items():
            lines.append(f"- {code}: `{doc.get('resource', '')}` - {doc.get('label', '')}")
        lines.append("")

    # Handling types
    handelingen = config.get("handelingen", {})
    if handelingen:
        lines.append("## Handling Types")
        for code, h in handelingen.items():
            lines.append(f"- {code}: `{h.get('resource', '')}` - {h.get('label', '')}")
        lines.append("")

    # Relations
    relaties = config.get("relaties", {})
    if relaties:
        lines.append("## Document Relations")
        for code, r in relaties.items():
            lines.append(f"- {code}: `{r.get('resource', '')}` - {r.get('label', '')}")
        lines.append("")

    # Template
    template = config.get("template", {})
    if template and "xml" in template:
        lines.append("## XML Template Example")
        lines.append("```xml")
        lines.append(template["xml"].strip())
        lines.append("```")

    return "\n".join(lines)


def get_xsd_schema_content() -> str:
    """Get the actual DIWOO XSD schema content.

    Returns:
        XSD schema as string
    """
    xsd_path = SCHEMAS_DIR / "diwoo-metadata.xsd"
    if not xsd_path.exists():
        raise InstructionNotFoundError(f"XSD schema not found at {xsd_path}")
    return xsd_path.read_text(encoding="utf-8")


def format_instruction_with_context(
    instruction: str,
    context: dict[str, str] | None = None,
) -> str:
    """Format an instruction with optional context variables.

    Args:
        instruction: Base instruction content
        context: Optional dict of variables to substitute

    Returns:
        Formatted instruction
    """
    if context is None:
        return instruction

    result = instruction
    for key, value in context.items():
        result = result.replace(f"{{{{{key}}}}}", value)

    return result
