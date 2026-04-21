"""Canonical normalized document schema used across ingestion and retrieval."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any


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


def _validate_iso_date(value: str | None, field_name: str) -> None:
    if value is None:
        return
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be ISO-8601 formatted (YYYY-MM-DD), got: {value}") from exc


@dataclass(frozen=True)
class NormalizedDocument:
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
    allowed_roles: tuple[str, ...] = field(default_factory=lambda: ("helpdesk", "inspector", "legal_counsel"))
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.doc_id.strip():
            raise ValueError("doc_id must not be empty")
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if not self.jurisdiction.strip():
            raise ValueError("jurisdiction must not be empty")
        if not self.text.strip():
            raise ValueError("text must not be empty")
        if not self.source_path.strip():
            raise ValueError("source_path must not be empty")
        if not self.allowed_roles:
            raise ValueError("allowed_roles must not be empty")
        _validate_iso_date(self.effective_date, "effective_date")
        _validate_iso_date(self.decision_date, "decision_date")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_type"] = self.source_type.value
        payload["security_classification"] = self.security_classification.value
        payload["allowed_roles"] = list(self.allowed_roles)
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NormalizedDocument":
        data = dict(payload)
        data["source_type"] = SourceType.from_value(data["source_type"])
        data["security_classification"] = SecurityClassification(data["security_classification"])
        data["allowed_roles"] = tuple(data.get("allowed_roles", ()))
        return cls(**data)
