"""Chunk schema for legal-aware retrieval records."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import Field, field_validator, model_validator

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
    valid_from: str | None = None
    valid_to: str | None = None
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

    @field_validator("valid_from", "valid_to")
    @classmethod
    def _validity_dates_are_iso(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            return None
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{info.field_name} must be ISO-8601 formatted (YYYY-MM-DD), got: {value}") from exc
        return value

    @model_validator(mode="after")
    def _valid_range_is_ordered(self) -> "ChunkRecord":
        if self.valid_from is not None and self.valid_to is not None:
            if date.fromisoformat(self.valid_to) < date.fromisoformat(self.valid_from):
                raise ValueError("valid_to must be on or after valid_from")
        return self

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ChunkRecord":
        return cls.model_validate(payload)
