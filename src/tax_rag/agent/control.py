"""Explicit corrective-RAG style control flow for local agent behavior."""

from __future__ import annotations

from dataclasses import dataclass

from tax_rag.agent.baseline import _answer_citations, _truncate_snippet, build_agent_response
from tax_rag.agent.evidence import grade_evidence
from tax_rag.agent.transform import transform_query
from tax_rag.common import DEFAULT_CONFIG
from tax_rag.retrieval import RetrievalMethod, RetrievalService
from tax_rag.schemas import (
    AgentResponse,
    AgentState,
    AnswerOutcome,
    EvidenceAssessment,
    EvidenceGrade,
    QueryTransformStrategy,
    RefusalReason,
    RetrievalMethod as RetrievalMethodEnum,
    RetrievalResponse,
    SourceType,
)


def _grade_rank(evidence: EvidenceAssessment) -> int:
    if evidence.grade is EvidenceGrade.RELEVANT:
        return 3
    if evidence.grade is EvidenceGrade.AMBIGUOUS:
        return 2
    return 1


def _choose_better_response(
    left: tuple[RetrievalResponse, EvidenceAssessment],
    right: tuple[RetrievalResponse, EvidenceAssessment],
) -> tuple[RetrievalResponse, EvidenceAssessment]:
    left_response, left_evidence = left
    right_response, right_evidence = right
    if _grade_rank(right_evidence) != _grade_rank(left_evidence):
        return right if _grade_rank(right_evidence) > _grade_rank(left_evidence) else left
    left_score = left_evidence.top_score or 0.0
    right_score = right_evidence.top_score or 0.0
    return right if right_score > left_score else left


def _combine_subquery_answers(
    *,
    query: str,
    role: str,
    subquery_results: list[tuple[str, RetrievalResponse, EvidenceAssessment]],
    state_trace: tuple[str, ...],
) -> AgentResponse:
    citations_by_chunk_id = {}
    fragments: list[str] = []
    for subquery, retrieval_response, _evidence in subquery_results:
        for citation in _answer_citations(retrieval_response):
            citations_by_chunk_id.setdefault(citation.chunk_id, citation)
        top_result = retrieval_response.results[0]
        fragments.append(f"For '{subquery}': {_truncate_snippet(top_result.text)}")

    combined_evidence = EvidenceAssessment(
        grade=EvidenceGrade.RELEVANT,
        explanation="All transformed sub-queries returned sufficiently relevant evidence.",
        result_count=sum(len(response.results) for _, response, _ in subquery_results),
        supporting_chunk_ids=tuple(
            chunk_id
            for _, _, evidence in subquery_results
            for chunk_id in evidence.supporting_chunk_ids
        ),
        top_score=max((evidence.top_score or 0.0) for _, _, evidence in subquery_results),
        metadata={"subquery_count": len(subquery_results)},
    )

    return AgentResponse(
        query=query,
        role=role,
        outcome=AnswerOutcome.ANSWERED,
        answer_text=" ".join(fragments),
        citations=tuple(citations_by_chunk_id.values()),
        evidence=combined_evidence,
        retrieval_method=RetrievalMethodEnum.HYBRID,
        state_trace=state_trace,
        metadata={
            "subqueries": [
                {
                    "query": subquery,
                    "retrieval_method": response.retrieval_method.value,
                    "evidence_grade": evidence.grade.value,
                }
                for subquery, response, evidence in subquery_results
            ]
        },
    )


def _refuse_for_subquery_failure(
    *,
    query: str,
    role: str,
    subquery_results: list[tuple[str, RetrievalResponse, EvidenceAssessment]],
    state_trace: tuple[str, ...],
) -> AgentResponse:
    worst = subquery_results[0]
    for candidate in subquery_results[1:]:
        if _grade_rank(candidate[2]) < _grade_rank(worst[2]):
            worst = candidate
    subquery, retrieval_response, evidence = worst
    response = build_agent_response(
        query=query,
        role=role,
        retrieval_response=retrieval_response,
        evidence=EvidenceAssessment(
            grade=EvidenceGrade.AMBIGUOUS if any(item[2].grade is EvidenceGrade.AMBIGUOUS for item in subquery_results) else EvidenceGrade.IRRELEVANT,
            explanation=f"Not all transformed sub-queries had sufficient evidence. Weakest sub-query: '{subquery}'.",
            result_count=sum(len(item[1].results) for item in subquery_results),
            supporting_chunk_ids=tuple(
                chunk_id
                for _, _, item_evidence in subquery_results
                for chunk_id in item_evidence.supporting_chunk_ids
            ),
            top_score=max((item[2].top_score or 0.0) for item in subquery_results),
            refusal_reason=evidence.refusal_reason or RefusalReason.INSUFFICIENT_EVIDENCE,
            metadata={
                "subquery_count": len(subquery_results),
                "subqueries": [
                    {
                        "query": item_query,
                        "grade": item_evidence.grade.value,
                        "refusal_reason": item_evidence.refusal_reason.value if item_evidence.refusal_reason else None,
                    }
                    for item_query, _item_response, item_evidence in subquery_results
                ],
            },
        ),
    )
    return response.model_copy(update={"state_trace": state_trace})


@dataclass
class CorrectiveRAGAgent:
    retrieval_service: RetrievalService

    def answer(
        self,
        query: str,
        role: str,
        top_k: int | None = None,
        *,
        method: RetrievalMethod | None = None,
        source_types: tuple[SourceType, ...] = (),
        jurisdiction: str | None = "NL",
    ) -> AgentResponse:
        plan = transform_query(query)
        states = [AgentState.UNDERSTOOD.value]
        if plan.strategy is not QueryTransformStrategy.NONE:
            states.append(AgentState.TRANSFORMED.value)

        if plan.strategy is QueryTransformStrategy.DECOMPOSITION:
            subquery_results: list[tuple[str, RetrievalResponse, EvidenceAssessment]] = []
            for subquery in plan.transformed_queries:
                states.append(AgentState.RETRIEVED.value)
                retrieval_response = self.retrieval_service.retrieve(
                    query=subquery,
                    role=role,
                    top_k=top_k,
                    method=method or RetrievalMethod.HYBRID,
                    source_types=source_types,
                    jurisdiction=jurisdiction,
                )
                states.append(AgentState.GRADED.value)
                evidence = grade_evidence(retrieval_response)
                subquery_results.append((subquery, retrieval_response, evidence))

            if subquery_results and all(evidence.grade is EvidenceGrade.RELEVANT for _, _, evidence in subquery_results):
                states.append(AgentState.ANSWERED.value)
                return _combine_subquery_answers(
                    query=query,
                    role=role,
                    subquery_results=subquery_results,
                    state_trace=tuple(states),
                )

            states.append(AgentState.REFUSED.value)
            return _refuse_for_subquery_failure(
                query=query,
                role=role,
                subquery_results=subquery_results,
                state_trace=tuple(states),
            )

        states.append(AgentState.RETRIEVED.value)
        retrieval_response = self.retrieval_service.retrieve(
            query=query,
            role=role,
            top_k=top_k,
            method=method,
            source_types=source_types,
            jurisdiction=jurisdiction,
        )
        states.append(AgentState.GRADED.value)
        evidence = grade_evidence(retrieval_response)

        if evidence.grade is EvidenceGrade.RELEVANT:
            states.append(AgentState.ANSWERED.value)
            response = build_agent_response(
                query=query,
                role=role,
                retrieval_response=retrieval_response,
                evidence=evidence,
            )
            return response.model_copy(
                update={
                    "state_trace": tuple(states),
                    "metadata": {**response.metadata, "transform_plan": plan.to_dict()},
                }
            )

        if (
            plan.strategy is QueryTransformStrategy.STRUCTURED_IDENTIFIER
            and DEFAULT_CONFIG.agent.max_retry_attempts > 0
            and plan.transformed_queries
        ):
            states.append(AgentState.RETRYING.value)
            best = (retrieval_response, evidence)
            for focused_query in plan.transformed_queries[: DEFAULT_CONFIG.agent.max_retry_attempts]:
                states.append(AgentState.RETRIEVED.value)
                retry_response = self.retrieval_service.retrieve(
                    query=focused_query,
                    role=role,
                    top_k=top_k,
                    method=RetrievalMethod.LEXICAL,
                    source_types=source_types,
                    jurisdiction=jurisdiction,
                )
                states.append(AgentState.GRADED.value)
                retry_evidence = grade_evidence(retry_response)
                best = _choose_better_response(best, (retry_response, retry_evidence))

            best_response, best_evidence = best
            terminal_state = AgentState.ANSWERED if best_evidence.grade is EvidenceGrade.RELEVANT else AgentState.REFUSED
            states.append(terminal_state.value)
            response = build_agent_response(
                query=query,
                role=role,
                retrieval_response=best_response,
                evidence=best_evidence,
            )
            return response.model_copy(
                update={
                    "state_trace": tuple(states),
                    "metadata": {
                        **response.metadata,
                        "transform_plan": plan.to_dict(),
                    },
                }
            )

        states.append(AgentState.REFUSED.value)
        response = build_agent_response(
            query=query,
            role=role,
            retrieval_response=retrieval_response,
            evidence=evidence,
        )
        return response.model_copy(
            update={
                "state_trace": tuple(states),
                "metadata": {**response.metadata, "transform_plan": plan.to_dict()},
            }
        )
