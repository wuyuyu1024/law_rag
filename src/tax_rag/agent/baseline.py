"""Evidence-gated local answer baseline without external model dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from tax_rag.agent.evidence import grade_evidence
from tax_rag.common import DEFAULT_CONFIG
from tax_rag.retrieval import RetrievalMethod, RetrievalService, resolve_result_citation
from tax_rag.schemas import (
    AgentResponse,
    AnswerCitation,
    AnswerOutcome,
    EvidenceAssessment,
    EvidenceGrade,
    RetrievalResponse,
    SourceType,
)


def _truncate_snippet(text: str) -> str:
    max_chars = DEFAULT_CONFIG.agent.snippet_max_chars
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def _answer_citations(response: RetrievalResponse) -> tuple[AnswerCitation, ...]:
    citations: list[AnswerCitation] = []
    for result in response.results[: DEFAULT_CONFIG.agent.max_answer_citations]:
        resolved = resolve_result_citation(result)
        citations.append(
            AnswerCitation(
                label=resolved.label,
                source_type=resolved.source_type,
                source_path=resolved.source_path,
                citation_path=resolved.citation_path,
                doc_id=resolved.doc_id,
                chunk_id=resolved.chunk_id,
            )
        )
    return tuple(citations)


def build_agent_response(
    *,
    query: str,
    role: str,
    retrieval_response: RetrievalResponse,
    evidence: EvidenceAssessment | None = None,
) -> AgentResponse:
    evidence = evidence or grade_evidence(retrieval_response)
    citations = _answer_citations(retrieval_response)

    if evidence.grade is not EvidenceGrade.RELEVANT:
        return AgentResponse(
            query=query,
            role=role,
            outcome=AnswerOutcome.REFUSED,
            citations=citations,
            evidence=evidence,
            retrieval_method=retrieval_response.retrieval_method,
            state_trace=("retrieved", "graded", "refused"),
            metadata={
                "retrieval_metadata": retrieval_response.metadata,
                "result_count": len(retrieval_response.results),
            },
        )

    fragments: list[str] = []
    for index, result in enumerate(retrieval_response.results[: DEFAULT_CONFIG.agent.max_answer_citations], start=1):
        prefix = "Primary evidence" if index == 1 else "Additional evidence"
        fragments.append(f"{prefix} from {result.source.citation_path}: {_truncate_snippet(result.text)}")

    return AgentResponse(
        query=query,
        role=role,
        outcome=AnswerOutcome.ANSWERED,
        answer_text=" ".join(fragments),
        citations=citations,
        evidence=evidence,
        retrieval_method=retrieval_response.retrieval_method,
        state_trace=("retrieved", "graded", "answered"),
        metadata={
            "retrieval_metadata": retrieval_response.metadata,
            "result_count": len(retrieval_response.results),
            "source_types": sorted({citation.source_type.value for citation in citations}),
        },
    )


@dataclass
class EvidenceGatedAgent:
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
        retrieval_response = self.retrieval_service.retrieve(
            query=query,
            role=role,
            top_k=top_k,
            method=method,
            source_types=source_types,
            jurisdiction=jurisdiction,
        )
        return build_agent_response(
            query=query,
            role=role,
            retrieval_response=retrieval_response,
        )
