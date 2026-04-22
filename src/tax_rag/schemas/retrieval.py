"""Typed retrieval contracts for inspectable retrieval outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from tax_rag.schemas.chunk import ChunkRecord
from tax_rag.schemas.document import SecurityClassification, SourceType


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


@dataclass(frozen=True)
class RetrievalRequest:
    query: str
    role: str
    top_k: int = 10
    source_types: tuple[SourceType, ...] = ()
    jurisdiction: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("query must not be empty")
        if not self.role.strip():
            raise ValueError("role must not be empty")
        if self.top_k <= 0:
            raise ValueError("top_k must be greater than 0")
        if self.jurisdiction is not None and not self.jurisdiction.strip():
            raise ValueError("jurisdiction must not be blank when provided")

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "role": self.role,
            "top_k": self.top_k,
            "source_types": [source_type.value for source_type in self.source_types],
            "jurisdiction": self.jurisdiction,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RetrievalRequest":
        data = dict(payload)
        data["source_types"] = tuple(SourceType.from_value(value) for value in data.get("source_types", ()))
        return cls(**data)


@dataclass(frozen=True)
class SourceReference:
    chunk_id: str
    doc_id: str
    source_path: str
    citation_path: str
    source_type: SourceType
    jurisdiction: str
    allowed_roles: tuple[str, ...]
    security_classification: SecurityClassification
    article: str | None = None
    paragraph: str | None = None
    subparagraph: str | None = None
    ecli: str | None = None
    court: str | None = None
    decision_date: str | None = None
    section_type: str | None = None

    def __post_init__(self) -> None:
        if not self.chunk_id.strip():
            raise ValueError("chunk_id must not be empty")
        if not self.doc_id.strip():
            raise ValueError("doc_id must not be empty")
        if not self.source_path.strip():
            raise ValueError("source_path must not be empty")
        if not self.citation_path.strip():
            raise ValueError("citation_path must not be empty")
        if not self.jurisdiction.strip():
            raise ValueError("jurisdiction must not be empty")
        if not self.allowed_roles:
            raise ValueError("allowed_roles must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "source_path": self.source_path,
            "citation_path": self.citation_path,
            "source_type": self.source_type.value,
            "jurisdiction": self.jurisdiction,
            "allowed_roles": list(self.allowed_roles),
            "security_classification": self.security_classification.value,
            "article": self.article,
            "paragraph": self.paragraph,
            "subparagraph": self.subparagraph,
            "ecli": self.ecli,
            "court": self.court,
            "decision_date": self.decision_date,
            "section_type": self.section_type,
        }

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
        data = dict(payload)
        data["source_type"] = SourceType.from_value(data["source_type"])
        data["security_classification"] = SecurityClassification(data["security_classification"])
        data["allowed_roles"] = tuple(data["allowed_roles"])
        return cls(**data)


@dataclass(frozen=True)
class ScoreTrace:
    metric: str
    value: float
    rank: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.metric.strip():
            raise ValueError("metric must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "value": self.value,
            "rank": self.rank,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ScoreTrace":
        return cls(**payload)


@dataclass(frozen=True)
class RetrievalResult:
    source: SourceReference
    text: str
    retrieval_method: RetrievalMethod
    scores: tuple[ScoreTrace, ...]
    matched_terms: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("text must not be empty")
        if not self.scores:
            raise ValueError("scores must not be empty")

    @property
    def chunk_id(self) -> str:
        return self.source.chunk_id

    @property
    def doc_id(self) -> str:
        return self.source.doc_id

    def score_map(self) -> dict[str, float]:
        return {score.metric: score.value for score in self.scores}

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source.to_dict(),
            "text": self.text,
            "retrieval_method": self.retrieval_method.value,
            "scores": [score.to_dict() for score in self.scores],
            "matched_terms": list(self.matched_terms),
            "metadata": dict(self.metadata),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

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
        data = dict(payload)
        data["source"] = SourceReference.from_dict(data["source"])
        data["retrieval_method"] = RetrievalMethod.from_value(data["retrieval_method"])
        data["scores"] = tuple(ScoreTrace.from_dict(score) for score in data["scores"])
        data["matched_terms"] = tuple(data.get("matched_terms", ()))
        return cls(**data)


@dataclass(frozen=True)
class RetrievalResponse:
    request: RetrievalRequest
    retrieval_method: RetrievalMethod
    results: tuple[RetrievalResult, ...]
    security_stage: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.security_stage.strip():
            raise ValueError("security_stage must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "retrieval_method": self.retrieval_method.value,
            "results": [result.to_dict() for result in self.results],
            "security_stage": self.security_stage,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RetrievalResponse":
        data = dict(payload)
        data["request"] = RetrievalRequest.from_dict(data["request"])
        data["retrieval_method"] = RetrievalMethod.from_value(data["retrieval_method"])
        data["results"] = tuple(RetrievalResult.from_dict(result) for result in data["results"])
        return cls(**data)

