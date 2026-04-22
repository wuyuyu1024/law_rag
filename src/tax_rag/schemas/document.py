"""Canonical normalized document schema used across ingestion and retrieval."""

from __future__ import annotations

import json
from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceType(StrEnum):
    LEGISLATION = "legislation"
    CASE_LAW = "case_law"
    INTERNAL_POLICY = "internal_policy"
    E_LEARNING = "e_learning"

    @classmethod
    def from_value(cls, value: str) -> "SourceType":
        try:
            return cls(value)
        except ValueError as exc:
            supported = ", ".join(member.value for member in cls)
            raise ValueError(f"Unsupported source type '{value}'. Supported values: {supported}") from exc


class SecurityClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


def _validate_iso_date(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be ISO-8601 formatted (YYYY-MM-DD), got: {value}") from exc
    return value


class SchemaModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)


class NormalizedDocument(SchemaModel):
    doc_id: str
    source_type: SourceType
    title: str
    jurisdiction: str
    text: str
    source_path: str
    effective_date: str | None = None
    article: str | None = None
    paragraph: str | None = None
    subparagraph: str | None = None
    citation_path: str | None = None
    ecli: str | None = None
    court: str | None = None
    decision_date: str | None = None
    section_type: str | None = None
    security_classification: SecurityClassification = SecurityClassification.PUBLIC
    allowed_roles: tuple[str, ...] = ("helpdesk", "inspector", "legal_counsel")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("doc_id", "title", "jurisdiction", "text", "source_path")
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

    @field_validator("effective_date")
    @classmethod
    def _effective_date_is_iso(cls, value: str | None) -> str | None:
        return _validate_iso_date(value, "effective_date")

    @field_validator("decision_date")
    @classmethod
    def _decision_date_is_iso(cls, value: str | None) -> str | None:
        return _validate_iso_date(value, "decision_date")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NormalizedDocument":
        return cls.model_validate(payload)
