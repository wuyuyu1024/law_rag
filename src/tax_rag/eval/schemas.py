"""Evaluation schemas for gold questions and regression reports."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from tax_rag.schemas import AnswerOutcome, EvidenceGrade, RefusalReason, RetrievalMethod
from tax_rag.schemas.document import SchemaModel


class GoldEvalCase(SchemaModel):
    case_id: str
    category: str
    query: str
    role: str
    expected_outcome: AnswerOutcome
    expected_grade: EvidenceGrade | None = None
    expected_refusal_reason: RefusalReason | None = None
    expected_citation_substrings: tuple[str, ...] = ()
    forbidden_citation_substrings: tuple[str, ...] = ()
    notes: str | None = None

    @field_validator("case_id", "category", "query", "role")
    @classmethod
    def _non_empty_string(cls, value: str, info: Any) -> str:
        if not value.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return value


class EvalCaseResult(SchemaModel):
    case_id: str
    category: str
    passed: bool
    outcome_match: bool
    grade_match: bool
    refusal_reason_match: bool
    citation_presence: bool
    expected_citation_match_count: int
    expected_citation_total: int
    unauthorized_retrieval_failure: bool
    faithfulness_proxy_pass: bool
    context_precision_proxy: float
    query: str
    role: str
    expected_outcome: AnswerOutcome
    actual_outcome: AnswerOutcome
    expected_grade: EvidenceGrade | None = None
    actual_grade: EvidenceGrade | None = None
    expected_refusal_reason: RefusalReason | None = None
    actual_refusal_reason: RefusalReason | None = None
    citations: tuple[str, ...] = ()
    state_trace: tuple[str, ...] = ()
    execution_trace: tuple[dict[str, Any], ...] = ()
    answer_text: str | None = None
    notes: str | None = None


class EvalReport(SchemaModel):
    generated_at: str
    total_cases: int
    passed_cases: int
    metrics: dict[str, float | int]
    cases: tuple[EvalCaseResult, ...]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("generated_at")
    @classmethod
    def _valid_datetime(cls, value: str) -> str:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value


class PromotionCheck(SchemaModel):
    name: str
    passed: bool
    comparator: str
    actual: float | int
    expected: float | int
    details: str | None = None


class PromotionDecision(SchemaModel):
    evaluated_at: str
    candidate_label: str
    passed: bool
    checks: tuple[PromotionCheck, ...]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evaluated_at")
    @classmethod
    def _valid_evaluated_at(cls, value: str) -> str:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value


class EvalTraceRecord(SchemaModel):
    case_id: str
    query: str
    role: str
    outcome: AnswerOutcome
    evidence_grade: EvidenceGrade | None = None
    refusal_reason: RefusalReason | None = None
    state_trace: tuple[str, ...] = ()
    execution_trace: tuple[dict[str, Any], ...] = ()


class LatencyCaseResult(SchemaModel):
    case_id: str
    category: str
    query: str
    role: str
    retrieval_method: RetrievalMethod
    outcome: AnswerOutcome
    evidence_grade: EvidenceGrade
    transform_strategy: str
    cache_enabled: bool
    retrieval_result_count: int
    target_ttft_ms: float
    total_uncached_ms: float
    target_met: bool
    stage_timings_ms: dict[str, float] = Field(default_factory=dict)
    notes: str | None = None


class LatencyReport(SchemaModel):
    generated_at: str
    total_cases: int
    cases_under_target: int
    target_ttft_ms: float
    metrics: dict[str, float | int]
    cases: tuple[LatencyCaseResult, ...]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("generated_at")
    @classmethod
    def _valid_datetime(cls, value: str) -> str:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value
