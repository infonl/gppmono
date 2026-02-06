"""Pydantic schemas with CamelCase serialization for TypeScript/JavaScript compatibility."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase.

    Args:
        string: Snake case string (e.g., 'gekoppelde_waardelijsten')

    Returns:
        CamelCase string (e.g., 'gekoppeldeWaardelijsten')
    """
    components = string.split("_")
    return components[0] + "".join(word.capitalize() for word in components[1:])


class CamelModel(BaseModel):
    """Base model that serializes to camelCase for TypeScript/JavaScript compatibility.

    Usage:
        class MyResponse(CamelModel):
            some_field: str
            another_field: int

        # Will serialize as:
        # {"someField": "value", "anotherField": 42}
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Serialize using aliases (camelCase) by default."""
        kwargs.setdefault("by_alias", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs: Any) -> str:
        """Serialize to JSON using aliases (camelCase) by default."""
        kwargs.setdefault("by_alias", True)
        return super().model_dump_json(**kwargs)
