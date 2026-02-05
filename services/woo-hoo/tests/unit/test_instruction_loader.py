"""Tests for the instruction loader service."""

from __future__ import annotations

import pytest

from woo_hoo.services.instruction_loader import (
    InstructionNotFoundError,
    get_diwoo_schema_instruction,
    list_instructions,
    load_instruction,
)


class TestInstructionLoader:
    """Tests for instruction loading functionality."""

    def test_list_instructions_returns_available(self):
        """Test that list_instructions returns available instruction files."""
        instructions = list_instructions()
        assert isinstance(instructions, list)
        assert "diwoo_schema" in instructions

    def test_load_instruction_diwoo_schema(self):
        """Test loading the DIWOO schema instruction."""
        content = load_instruction("diwoo_schema")
        assert isinstance(content, str)
        assert len(content) > 100
        assert "DIWOO" in content
        assert "informatiecategorieen" in content.lower()

    def test_load_instruction_not_found(self):
        """Test that loading non-existent instruction raises error."""
        with pytest.raises(InstructionNotFoundError) as exc_info:
            load_instruction("nonexistent_instruction")
        assert "nonexistent_instruction" in str(exc_info.value)
        assert "Available:" in str(exc_info.value)

    def test_get_diwoo_schema_instruction(self):
        """Test the convenience function for DIWOO schema."""
        content = get_diwoo_schema_instruction()
        assert isinstance(content, str)
        # Check for key schema elements
        assert "WOO_VERZOEKEN" in content
        assert "ADVIEZEN" in content
        assert "JSON" in content
        assert "ISO 8601" in content or "YYYY-MM-DD" in content


class TestDiwooSchemaContent:
    """Tests for DIWOO schema instruction content."""

    @pytest.fixture
    def schema_content(self) -> str:
        """Load the schema content for tests."""
        return get_diwoo_schema_instruction()

    def test_contains_all_17_categories(self, schema_content: str):
        """Test that schema contains all 17 Woo categories."""
        required_categories = [
            "WETTEN_AVV",
            "OVERIGE_BESLUITEN_AS",
            "ONTWERPEN_REGELGEVING",
            "ORGANISATIE_WERKWIJZE",
            "BEREIKBAARHEID",
            "INGEKOMEN_STUKKEN",
            "VERGADERSTUKKEN_SG",
            "VERGADERSTUKKEN_DECENTRAAL",
            "AGENDAS_BESLUITENLIJSTEN",
            "ADVIEZEN",
            "CONVENANTEN",
            "JAARPLANNEN_JAARVERSLAGEN",
            "SUBSIDIES_ANDERS",
            "WOO_VERZOEKEN",
            "ONDERZOEKSRAPPORTEN",
            "BESCHIKKINGEN",
            "KLACHTOORDELEN",
        ]
        for category in required_categories:
            assert category in schema_content, f"Missing category: {category}"

    def test_contains_json_format_example(self, schema_content: str):
        """Test that schema contains JSON format examples."""
        assert "```json" in schema_content
        assert '"officieleTitel"' in schema_content or '"officiele_titel"' in schema_content.lower()

    def test_contains_document_types(self, schema_content: str):
        """Test that schema contains document types."""
        document_types = ["BRIEF", "ADVIES", "RAPPORT", "BESLUIT"]
        for doc_type in document_types:
            assert doc_type in schema_content, f"Missing document type: {doc_type}"

    def test_contains_date_format_instruction(self, schema_content: str):
        """Test that schema specifies date format."""
        assert "YYYY-MM-DD" in schema_content or "ISO 8601" in schema_content
