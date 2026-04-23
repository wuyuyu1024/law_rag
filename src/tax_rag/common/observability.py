"""Structured trace helpers for demo observability and regression debugging."""

from __future__ import annotations

from typing import Any

from tax_rag.common.config import DEFAULT_CONFIG
from tax_rag.schemas import AgentResponse, EvidenceAssessment, QueryTransformPlan, RetrievalResponse


def trace_event(
    *,
    sequence: int,
    event: str,
    state: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "event": event,
        "state": state,
        "payload": payload or {},
    }


def transform_trace_event(sequence: int, plan: QueryTransformPlan) -> dict[str, Any]:
    return trace_event(
        sequence=sequence,
        event="query_transform_planned",
        state="transformed" if plan.transformed_queries else "understood",
        payload={
            "strategy": plan.strategy.value,
            "transformed_queries": list(plan.transformed_queries),
            "rationale": plan.rationale,
            "metadata": dict(plan.metadata),
        },
    )


def retrieval_trace_event(
    sequence: int,
    response: RetrievalResponse,
    *,
    query: str,
    attempt_label: str,
) -> dict[str, Any]:
    top_results: list[dict[str, Any]] = []
    for result in response.results[: DEFAULT_CONFIG.agent.trace_top_results]:
        top_results.append(
            {
                "chunk_id": result.chunk_id,
                "doc_id": result.doc_id,
                "citation_path": result.source.citation_path,
                "source_type": result.source.source_type.value,
                "matched_terms": list(result.matched_terms),
                "scores": result.score_map(),
            }
        )

    return trace_event(
        sequence=sequence,
        event="retrieval_completed",
        state="retrieved",
        payload={
            "query": query,
            "attempt_label": attempt_label,
            "retrieval_method": response.retrieval_method.value,
            "result_count": len(response.results),
            "security_stage": response.security_stage,
            "authorized_candidate_count": response.metadata.get("authorized_candidate_count", 0),
            "denied_count": response.metadata.get("denied_count", 0),
            "timings_ms": response.metadata.get("timings_ms", {}),
            "top_results": top_results,
        },
    )


def evidence_trace_event(
    sequence: int,
    evidence: EvidenceAssessment,
    *,
    query: str,
    attempt_label: str,
) -> dict[str, Any]:
    return trace_event(
        sequence=sequence,
        event="evidence_graded",
        state="graded",
        payload={
            "query": query,
            "attempt_label": attempt_label,
            "grade": evidence.grade.value,
            "refusal_reason": evidence.refusal_reason.value if evidence.refusal_reason else None,
            "top_score": evidence.top_score,
            "supporting_chunk_ids": list(evidence.supporting_chunk_ids),
            "conflicting_chunk_ids": list(evidence.conflicting_chunk_ids),
            "explanation": evidence.explanation,
        },
    )


def retry_trace_event(sequence: int, *, focused_query: str) -> dict[str, Any]:
    return trace_event(
        sequence=sequence,
        event="retry_scheduled",
        state="retrying",
        payload={"focused_query": focused_query},
    )


def response_trace_event(sequence: int, response: AgentResponse) -> dict[str, Any]:
    return trace_event(
        sequence=sequence,
        event="response_finalized",
        state=response.outcome.value,
        payload={
            "outcome": response.outcome.value,
            "refusal_reason": response.evidence.refusal_reason.value if response.evidence.refusal_reason else None,
            "citation_paths": [citation.citation_path for citation in response.citations],
            "state_trace": list(response.state_trace),
        },
    )
