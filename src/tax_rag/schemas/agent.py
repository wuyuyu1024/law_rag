"""Agent state and query transformation contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator

from tax_rag.schemas.document import SchemaModel


class AgentState(StrEnum):
    UNDERSTOOD = "understood"
    TRANSFORMED = "transformed"
    RETRIEVED = "retrieved"
    GRADED = "graded"
    RETRYING = "retrying"
    ANSWERED = "answered"
    REFUSED = "refused"


class QueryTransformStrategy(StrEnum):
    NONE = "none"
    STRUCTURED_IDENTIFIER = "structured_identifier"
    DECOMPOSITION = "decomposition"


class QueryTransformPlan(SchemaModel):
    original_query: str
    strategy: QueryTransformStrategy
    transformed_queries: tuple[str, ...] = ()
    rationale: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("original_query", "rationale")
    @classmethod
    def _non_empty_string(cls, value: str, info: Any) -> str:
        if not value.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return value
