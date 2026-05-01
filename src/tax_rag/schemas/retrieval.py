"""Typed retrieval contracts for inspectable retrieval outputs."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator

from tax_rag.schemas.chunk import ChunkRecord
from tax_rag.schemas.document import SchemaModel, SecurityClassification, SourceType


class RetrievalMethod(StrEnum):
    LEXICAL = "lexical"
    DENSE = "dense"
    HYBRID = "hybrid"

    @classmethod
    def from_value(cls, value: str) -> "RetrievalMethod":
        try:
            return cls(value)
        except ValueError as exc:
            supported = ", ".join(member.value for member in cls)
            raise ValueError(f"Unsupported retrieval method '{value}'. Supported values: {supported}") from exc


class RetrievalRequest(SchemaModel):
    query: str
    role: str
    top_k: int = 10
    source_types: tuple[SourceType, ...] = ()
    jurisdiction: str | None = None
    as_of_date: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("query", "role")
    @classmethod
    def _non_empty_string(cls, value: str, info: Any) -> str:
        if not value.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return value

    @field_validator("top_k")
    @classmethod
    def _positive_top_k(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("top_k must be greater than 0")
        return value

    @field_validator("jurisdiction")
    @classmethod
    def _non_blank_jurisdiction(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("jurisdiction must not be blank when provided")
        return value

    @field_validator("as_of_date")
    @classmethod
    def _as_of_date_is_iso(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"as_of_date must be ISO-8601 formatted (YYYY-MM-DD), got: {value}") from exc
        return value

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RetrievalRequest":
        return cls.model_validate(payload)


class SourceReference(SchemaModel):
    chunk_id: str
    doc_id: str
    source_path: str
    citation_path: str
    source_type: SourceType
    jurisdiction: str
    allowed_roles: tuple[str, ...]
    security_classification: SecurityClassification
    valid_from: str | None = None
    valid_to: str | None = None
    article: str | None = None
    paragraph: str | None = None
    subparagraph: str | None = None
    ecli: str | None = None
    court: str | None = None
    decision_date: str | None = None
    section_type: str | None = None

    @field_validator("chunk_id", "doc_id", "source_path", "citation_path", "jurisdiction")
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
    def from_chunk(cls, chunk: ChunkRecord) -> "SourceReference":
        return cls(
            chunk_id=chunk.chunk_id,
            doc_id=chunk.doc_id,
            source_path=chunk.source_path,
            citation_path=chunk.citation_path,
            source_type=chunk.source_type,
            jurisdiction=chunk.jurisdiction,
            allowed_roles=chunk.allowed_roles,
            security_classification=chunk.security_classification,
            valid_from=chunk.valid_from,
            valid_to=chunk.valid_to,
            article=chunk.article,
            paragraph=chunk.paragraph,
            subparagraph=chunk.subparagraph,
            ecli=chunk.ecli,
            court=chunk.court,
            decision_date=chunk.decision_date,
            section_type=chunk.section_type,
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceReference":
        return cls.model_validate(payload)


class ScoreTrace(SchemaModel):
    metric: str
    value: float
    rank: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metric")
    @classmethod
    def _metric_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("metric must not be empty")
        return value

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ScoreTrace":
        return cls.model_validate(payload)


class RetrievalResult(SchemaModel):
    source: SourceReference
    text: str
    retrieval_method: RetrievalMethod
    scores: tuple[ScoreTrace, ...]
    matched_terms: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def _text_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be empty")
        return value

    @field_validator("scores")
    @classmethod
    def _scores_must_not_be_empty(cls, value: tuple[ScoreTrace, ...]) -> tuple[ScoreTrace, ...]:
        if not value:
            raise ValueError("scores must not be empty")
        return value

    @property
    def chunk_id(self) -> str:
        return self.source.chunk_id

    @property
    def doc_id(self) -> str:
        return self.source.doc_id

    def score_map(self) -> dict[str, float]:
        return {score.metric: score.value for score in self.scores}

    @classmethod
    def from_chunk(
        cls,
        chunk: ChunkRecord,
        *,
        retrieval_method: RetrievalMethod,
        scores: tuple[ScoreTrace, ...],
        matched_terms: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> "RetrievalResult":
        return cls(
            source=SourceReference.from_chunk(chunk),
            text=chunk.text,
            retrieval_method=retrieval_method,
            scores=scores,
            matched_terms=matched_terms,
            metadata=metadata or {},
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RetrievalResult":
        return cls.model_validate(payload)


class RetrievalResponse(SchemaModel):
    request: RetrievalRequest
    retrieval_method: RetrievalMethod
    results: tuple[RetrievalResult, ...]
    security_stage: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("security_stage")
    @classmethod
    def _security_stage_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("security_stage must not be empty")
        return value

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RetrievalResponse":
        return cls.model_validate(payload)
