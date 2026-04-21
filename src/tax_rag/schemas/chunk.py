"""Chunk schema for legal-aware retrieval records."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from tax_rag.schemas.document import SecurityClassification, SourceType


@dataclass(frozen=True)
class ChunkRecord:
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
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.chunk_id.strip():
            raise ValueError("chunk_id must not be empty")
        if not self.doc_id.strip():
            raise ValueError("doc_id must not be empty")
        if not self.text.strip():
            raise ValueError("text must not be empty")
        if not self.citation_path.strip():
            raise ValueError("citation_path must not be empty")
        if not self.allowed_roles:
            raise ValueError("allowed_roles must not be empty")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_type"] = self.source_type.value
        payload["security_classification"] = self.security_classification.value
        payload["allowed_roles"] = list(self.allowed_roles)
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ChunkRecord":
        data = dict(payload)
        data["source_type"] = SourceType(data["source_type"])
        data["security_classification"] = SecurityClassification(data["security_classification"])
        data["allowed_roles"] = tuple(data["allowed_roles"])
        return cls(**data)
