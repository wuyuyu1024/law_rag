"""Typed answer and refusal contracts for evidence-gated generation."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator

from tax_rag.schemas.document import SchemaModel, SourceType
from tax_rag.schemas.retrieval import RetrievalMethod


class EvidenceGrade(StrEnum):
    RELEVANT = "relevant"
    AMBIGUOUS = "ambiguous"
    IRRELEVANT = "irrelevant"


class RefusalReason(StrEnum):
    NO_AUTHORIZED_SOURCE = "no_authorized_source"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    OUTDATED_EVIDENCE = "outdated_evidence"


class AnswerOutcome(StrEnum):
    ANSWERED = "answered"
    REFUSED = "refused"


class AnswerCitation(SchemaModel):
    label: str
    source_type: SourceType
    source_path: str
    citation_path: str
    doc_id: str
    chunk_id: str

    @field_validator("label", "source_path", "citation_path", "doc_id", "chunk_id")
    @classmethod
    def _non_empty_string(cls, value: str, info: Any) -> str:
        if not value.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return value


class EvidenceAssessment(SchemaModel):
    grade: EvidenceGrade
    explanation: str
    result_count: int
    supporting_chunk_ids: tuple[str, ...] = ()
    top_score: float | None = None
    refusal_reason: RefusalReason | None = None
    conflicting_chunk_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("explanation")
    @classmethod
    def _non_empty_explanation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("explanation must not be empty")
        return value


class AgentResponse(SchemaModel):
    query: str
    role: str
    outcome: AnswerOutcome
    answer_text: str | None = None
    citations: tuple[AnswerCitation, ...] = ()
    evidence: EvidenceAssessment
    retrieval_method: RetrievalMethod
    state_trace: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("query", "role")
    @classmethod
    def _non_empty_string(cls, value: str, info: Any) -> str:
        if not value.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return value
