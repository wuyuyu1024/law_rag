"""Deterministic evidence grading for retrieval outputs."""

from __future__ import annotations

import re

from tax_rag.common import DEFAULT_CONFIG
from tax_rag.schemas import (
    EvidenceAssessment,
    EvidenceGrade,
    RefusalReason,
    RetrievalMethod,
    RetrievalResponse,
)

_YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")
_GENERIC_ELIGIBILITY_PATTERN = re.compile(r"\b(?:if someone|can they|can someone|qualified|qualify|eligible)\b", re.IGNORECASE)
_EXACT_MATCH_METRICS = {
    "ecli_exact_match",
    "article_exact_match",
    "paragraph_exact_match",
    "subparagraph_exact_match",
    "citation_path_exact_match",
}
_TOKEN_PATTERN = re.compile(r"[a-z0-9%:.+-]+", re.IGNORECASE)


def _primary_score(response: RetrievalResponse, score_map: dict[str, float]) -> float:
    if response.retrieval_method is RetrievalMethod.HYBRID:
        if "rerank_score" in score_map:
            return score_map["rerank_score"]
        return score_map.get("rrf_score", 0.0)
    if response.retrieval_method is RetrievalMethod.LEXICAL:
        return score_map.get("lexical_score", 0.0)
    return score_map.get("dense_score", score_map.get("qdrant_score", 0.0))


def _is_relevant_score(response: RetrievalResponse, score_map: dict[str, float], primary_score: float) -> bool:
    if response.retrieval_method is RetrievalMethod.HYBRID and "rerank_score" in score_map:
        return primary_score >= DEFAULT_CONFIG.agent.relevant_rerank_score_threshold
    if response.retrieval_method is RetrievalMethod.HYBRID:
        return primary_score >= DEFAULT_CONFIG.agent.relevant_rrf_score_threshold
    if response.retrieval_method is RetrievalMethod.LEXICAL:
        return primary_score >= DEFAULT_CONFIG.agent.relevant_lexical_score_threshold
    return primary_score >= DEFAULT_CONFIG.agent.relevant_dense_score_threshold


def _is_ambiguous_score(response: RetrievalResponse, score_map: dict[str, float], primary_score: float) -> bool:
    if response.retrieval_method is RetrievalMethod.HYBRID and "rerank_score" in score_map:
        return primary_score >= DEFAULT_CONFIG.agent.ambiguous_rerank_score_floor
    if response.retrieval_method is RetrievalMethod.HYBRID:
        return primary_score >= DEFAULT_CONFIG.agent.ambiguous_rrf_score_floor
    if response.retrieval_method is RetrievalMethod.LEXICAL:
        return primary_score >= DEFAULT_CONFIG.agent.ambiguous_lexical_score_floor
    return primary_score >= DEFAULT_CONFIG.agent.ambiguous_dense_score_floor


def _prefer_no_authorized_source(response: RetrievalResponse, score_map: dict[str, float], primary_score: float) -> bool:
    if response.metadata.get("denied_count", 0) <= 0:
        return False
    if primary_score >= DEFAULT_CONFIG.agent.ambiguous_rerank_score_floor:
        return False
    if len(_TOKEN_PATTERN.findall(response.request.query)) < 3:
        return False
    return score_map.get("rerank_concept_overlap", 0.0) == 0.0 and score_map.get("rerank_lexical_overlap", 0.0) == 0.0


def _query_year(query: str) -> int | None:
    matches = [int(match.group(0)) for match in _YEAR_PATTERN.finditer(query)]
    return max(matches) if matches else None


def grade_evidence(response: RetrievalResponse) -> EvidenceAssessment:
    if not response.results:
        refusal_reason = (
            RefusalReason.NO_AUTHORIZED_SOURCE
            if response.metadata.get("denied_count", 0) > 0 and response.metadata.get("authorized_candidate_count", 0) == 0
            else RefusalReason.INSUFFICIENT_EVIDENCE
        )
        explanation = (
            "No authorized retrieval evidence was available for this role."
            if refusal_reason is RefusalReason.NO_AUTHORIZED_SOURCE
            else "Retrieval returned no sufficiently relevant evidence."
        )
        return EvidenceAssessment(
            grade=EvidenceGrade.IRRELEVANT,
            explanation=explanation,
            result_count=0,
            refusal_reason=refusal_reason,
            metadata=dict(response.metadata),
        )

    top_result = response.results[0]
    top_score_map = top_result.score_map()
    top_score = _primary_score(response, top_score_map)
    exact_match = any(metric in top_score_map for metric in _EXACT_MATCH_METRICS)

    query_year = _query_year(response.request.query)
    if (
        query_year is not None
        and response.results
        and all(
            result.source.decision_date is not None and int(result.source.decision_date[:4]) < query_year
            for result in response.results[: min(2, len(response.results))]
            if result.source.decision_date is not None
        )
        and any(result.source.decision_date is not None for result in response.results[: min(2, len(response.results))])
    ):
        return EvidenceAssessment(
            grade=EvidenceGrade.AMBIGUOUS,
            explanation="Retrieved evidence appears older than the year referenced in the query.",
            result_count=len(response.results),
            supporting_chunk_ids=tuple(result.chunk_id for result in response.results[:2]),
            top_score=top_score,
            refusal_reason=RefusalReason.OUTDATED_EVIDENCE,
            metadata=dict(response.metadata),
        )

    if (
        _GENERIC_ELIGIBILITY_PATTERN.search(response.request.query)
        and not exact_match
        and response.results
        and all(result.source.source_type.value == "case_law" for result in response.results[: min(2, len(response.results))])
    ):
        return EvidenceAssessment(
            grade=EvidenceGrade.AMBIGUOUS,
            explanation="Retrieved evidence is fact-specific case law without a general statutory basis.",
            result_count=len(response.results),
            supporting_chunk_ids=tuple(result.chunk_id for result in response.results[:2]),
            top_score=top_score,
            refusal_reason=RefusalReason.INSUFFICIENT_EVIDENCE,
            metadata=dict(response.metadata),
        )

    if exact_match:
        return EvidenceAssessment(
            grade=EvidenceGrade.RELEVANT,
            explanation="Retrieved evidence is sufficiently specific to support an answer.",
            result_count=len(response.results),
            supporting_chunk_ids=tuple(result.chunk_id for result in response.results[:2]),
            top_score=top_score,
            metadata=dict(response.metadata),
        )

    if len(response.results) >= 2:
        second_result = response.results[1]
        second_score_map = second_result.score_map()
        second_score = _primary_score(response, second_score_map)
        if (
            _is_ambiguous_score(response, top_score_map, top_score)
            and _is_ambiguous_score(response, second_score_map, second_score)
            and
            top_result.doc_id != second_result.doc_id
            and abs(top_score - second_score) <= DEFAULT_CONFIG.agent.conflicting_score_margin
        ):
            return EvidenceAssessment(
                grade=EvidenceGrade.AMBIGUOUS,
                explanation="Top retrieval candidates conflict because multiple sources rank nearly the same.",
                result_count=len(response.results),
                supporting_chunk_ids=(top_result.chunk_id, second_result.chunk_id),
                conflicting_chunk_ids=(top_result.chunk_id, second_result.chunk_id),
                top_score=top_score,
                refusal_reason=RefusalReason.CONFLICTING_EVIDENCE,
                metadata=dict(response.metadata),
            )

    if _is_relevant_score(response, top_score_map, top_score):
        return EvidenceAssessment(
            grade=EvidenceGrade.RELEVANT,
            explanation="Retrieved evidence is sufficiently specific to support an answer.",
            result_count=len(response.results),
            supporting_chunk_ids=tuple(result.chunk_id for result in response.results[:2]),
            top_score=top_score,
            metadata=dict(response.metadata),
        )

    if _is_ambiguous_score(response, top_score_map, top_score):
        return EvidenceAssessment(
            grade=EvidenceGrade.AMBIGUOUS,
            explanation="Retrieved evidence is partially relevant but not strong enough for a safe answer.",
            result_count=len(response.results),
            supporting_chunk_ids=tuple(result.chunk_id for result in response.results[:2]),
            top_score=top_score,
            refusal_reason=RefusalReason.INSUFFICIENT_EVIDENCE,
            metadata=dict(response.metadata),
        )

    refusal_reason = (
        RefusalReason.NO_AUTHORIZED_SOURCE
        if _prefer_no_authorized_source(response, top_score_map, top_score)
        else RefusalReason.INSUFFICIENT_EVIDENCE
    )
    return EvidenceAssessment(
        grade=EvidenceGrade.IRRELEVANT,
        explanation="Retrieved evidence is too weak to support an answer.",
        result_count=len(response.results),
        supporting_chunk_ids=tuple(result.chunk_id for result in response.results[:1]),
        top_score=top_score,
        refusal_reason=refusal_reason,
        metadata=dict(response.metadata),
    )
