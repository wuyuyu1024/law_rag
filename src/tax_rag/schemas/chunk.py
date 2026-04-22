"""Chunk schema for legal-aware retrieval records."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from tax_rag.schemas.document import SchemaModel, SecurityClassification, SourceType


class ChunkRecord(SchemaModel):
    chunk_id: str
    doc_id: str
    text: str
    citation_path: str
    source_type: SourceType
    jurisdiction: str
    allowed_roles: tuple[str, ...]
    source_path: str
    article: str | None = None
    paragraph: str | None = None
    subparagraph: str | None = None
    ecli: str | None = None
    court: str | None = None
    decision_date: str | None = None
    section_type: str | None = None
    security_classification: SecurityClassification = SecurityClassification.PUBLIC
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("chunk_id", "doc_id", "text", "citation_path", "jurisdiction", "source_path")
    @classmethod
    def _non_empty_string(cls, value: str, info: Any) -> str:
        if not value.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return value

    @field_validator("allowed_roles")
    @classmethod
    def _roles_must_not_be_empty(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("allowed_roles must not be empty")
        return value

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ChunkRecord":
        return cls.model_validate(payload)
