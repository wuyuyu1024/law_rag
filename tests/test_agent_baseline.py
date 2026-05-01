from tax_rag.agent import EvidenceGatedAgent, build_agent_response, grade_evidence
from tax_rag.retrieval import RetrievalMethod, RetrievalService
from tax_rag.schemas import (
    AnswerOutcome,
    ChunkRecord,
    EvidenceGrade,
    RefusalReason,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    ScoreTrace,
    SecurityClassification,
    SourceType,
)


def _chunk(
    *,
    chunk_id: str,
    source_type: SourceType,
    text: str,
    citation_path: str,
    allowed_roles: tuple[str, ...],
    security_classification: SecurityClassification,
    article: str | None = None,
    paragraph: str | None = None,
    ecli: str | None = None,
    decision_date: str | None = None,
) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=chunk_id,
        doc_id=f"doc:{chunk_id}",
        text=text,
        citation_path=citation_path,
        source_type=source_type,
        jurisdiction="NL",
        allowed_roles=allowed_roles,
        source_path=f"fixtures/{chunk_id}.xml",
        article=article,
        paragraph=paragraph,
        ecli=ecli,
        decision_date=decision_date,
        security_classification=security_classification,
    )


def test_grade_evidence_marks_exact_match_relevant() -> None:
    chunk = _chunk(
        chunk_id="case-ecli",
        source_type=SourceType.CASE_LAW,
        text="Holding on deductibility.",
        citation_path="ECLI:NL:HR:2025:99 > Beslissing > 1",
        allowed_roles=("legal_counsel",),
        security_classification=SecurityClassification.INTERNAL,
        ecli="ECLI:NL:HR:2025:99",
        decision_date="2025-01-17",
    )
    response = RetrievalResponse(
        request=RetrievalRequest(query="ECLI:NL:HR:2025:99", role="legal_counsel"),
        retrieval_method=RetrievalMethod.LEXICAL,
        results=(
            RetrievalResult.from_chunk(
                chunk,
                retrieval_method=RetrievalMethod.LEXICAL,
                scores=(
                    ScoreTrace(metric="ecli_exact_match", value=300.0, rank=1),
                    ScoreTrace(metric="lexical_score", value=300.0, rank=1),
                ),
            ),
        ),
        security_stage="pre_retrieval",
    )

    evidence = grade_evidence(response)

    assert evidence.grade is EvidenceGrade.RELEVANT
    assert evidence.refusal_reason is None


def test_grade_evidence_keeps_exact_hybrid_match_relevant_despite_close_dense_neighbor() -> None:
    exact_chunk = _chunk(
        chunk_id="law-10ec-1",
        source_type=SourceType.LEGISLATION,
        text="Lid 1. Voor ingekomen werknemers bedraagt de looptijd maximaal vijf jaar.",
        citation_path="Uitvoeringsbesluit loonbelasting 1965 > Artikel 10ec > Lid 1",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="10ec",
        paragraph="1",
    )
    dense_neighbor = _chunk(
        chunk_id="law-3-11-3",
        source_type=SourceType.LEGISLATION,
        text="Unrelated dense neighbor with a close fused score.",
        citation_path="Algemene wet bestuursrecht > Artikel 3:11 > Lid 3",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="3:11",
        paragraph="3",
    )
    response = RetrievalResponse(
        request=RetrievalRequest(query="Artikel 10ec lid 1", role="helpdesk"),
        retrieval_method=RetrievalMethod.HYBRID,
        results=(
            RetrievalResult.from_chunk(
                exact_chunk,
                retrieval_method=RetrievalMethod.HYBRID,
                scores=(
                    ScoreTrace(metric="article_exact_match", value=120.0, rank=1),
                    ScoreTrace(metric="paragraph_exact_match", value=20.0, rank=1),
                    ScoreTrace(metric="rrf_score", value=0.020, rank=1),
                ),
            ),
            RetrievalResult.from_chunk(
                dense_neighbor,
                retrieval_method=RetrievalMethod.HYBRID,
                scores=(ScoreTrace(metric="rrf_score", value=0.019, rank=2),),
            ),
        ),
        security_stage="pre_retrieval",
    )

    evidence = grade_evidence(response)

    assert evidence.grade is EvidenceGrade.RELEVANT
    assert evidence.refusal_reason is None


def test_grade_evidence_marks_close_top_results_ambiguous() -> None:
    chunk_a = _chunk(
        chunk_id="law-a",
        source_type=SourceType.LEGISLATION,
        text="Home office deduction text A.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 3.16",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="3.16",
    )
    chunk_b = _chunk(
        chunk_id="law-b",
        source_type=SourceType.LEGISLATION,
        text="Home office deduction text B.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 3.17",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="3.17",
    )
    response = RetrievalResponse(
        request=RetrievalRequest(query="home office deduction", role="helpdesk"),
        retrieval_method=RetrievalMethod.HYBRID,
        results=(
            RetrievalResult.from_chunk(
                chunk_a,
                retrieval_method=RetrievalMethod.HYBRID,
                scores=(ScoreTrace(metric="rrf_score", value=0.020, rank=1),),
            ),
            RetrievalResult.from_chunk(
                chunk_b,
                retrieval_method=RetrievalMethod.HYBRID,
                scores=(ScoreTrace(metric="rrf_score", value=0.018, rank=2),),
            ),
        ),
        security_stage="pre_retrieval",
    )

    evidence = grade_evidence(response)

    assert evidence.grade is EvidenceGrade.AMBIGUOUS
    assert evidence.refusal_reason is RefusalReason.CONFLICTING_EVIDENCE


def test_evidence_gated_agent_answers_with_citations_for_relevant_evidence() -> None:
    service = RetrievalService(
        chunks=[
            _chunk(
                chunk_id="law-home-office",
                source_type=SourceType.LEGISLATION,
                text="Lid 2 onderdeel a text about home office expense deductions.",
                citation_path="Wet inkomstenbelasting 2001 > Artikel 3.114 > Lid 2",
                allowed_roles=("helpdesk", "inspector", "legal_counsel"),
                security_classification=SecurityClassification.PUBLIC,
                article="3.114",
                paragraph="2",
            )
        ],
        default_method=RetrievalMethod.LEXICAL,
    )
    agent = EvidenceGatedAgent(retrieval_service=service)

    response = agent.answer("Artikel 3.114 lid 2", "helpdesk")

    assert response.outcome is AnswerOutcome.ANSWERED
    assert response.evidence.grade is EvidenceGrade.RELEVANT
    assert response.citations[0].citation_path == "Wet inkomstenbelasting 2001 > Artikel 3.114 > Lid 2"
    assert "Primary evidence from Wet inkomstenbelasting 2001 > Artikel 3.114 > Lid 2" in response.answer_text


def test_evidence_gated_agent_refuses_when_no_authorized_source_is_available() -> None:
    service = RetrievalService(
        chunks=[
            _chunk(
                chunk_id="restricted-policy",
                source_type=SourceType.INTERNAL_POLICY,
                text="Restricted fraud guidance.",
                citation_path="Fraud Manual > Scope",
                allowed_roles=("inspector", "legal_counsel"),
                security_classification=SecurityClassification.RESTRICTED,
            )
        ],
        default_method=RetrievalMethod.DENSE,
    )
    agent = EvidenceGatedAgent(retrieval_service=service)

    response = agent.answer("fraud guidance", "helpdesk")

    assert response.outcome is AnswerOutcome.REFUSED
    assert response.evidence.grade is EvidenceGrade.IRRELEVANT
    assert response.evidence.refusal_reason is RefusalReason.NO_AUTHORIZED_SOURCE


def test_build_agent_response_refuses_ambiguous_evidence() -> None:
    chunk_a = _chunk(
        chunk_id="law-a",
        source_type=SourceType.LEGISLATION,
        text="Home office deduction text A.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 3.16",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="3.16",
    )
    chunk_b = _chunk(
        chunk_id="law-b",
        source_type=SourceType.LEGISLATION,
        text="Home office deduction text B.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 3.17",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="3.17",
    )
    retrieval_response = RetrievalResponse(
        request=RetrievalRequest(query="home office deduction", role="helpdesk"),
        retrieval_method=RetrievalMethod.HYBRID,
        results=(
            RetrievalResult.from_chunk(
                chunk_a,
                retrieval_method=RetrievalMethod.HYBRID,
                scores=(ScoreTrace(metric="rrf_score", value=0.020, rank=1),),
            ),
            RetrievalResult.from_chunk(
                chunk_b,
                retrieval_method=RetrievalMethod.HYBRID,
                scores=(ScoreTrace(metric="rrf_score", value=0.018, rank=2),),
            ),
        ),
        security_stage="pre_retrieval",
    )

    response = build_agent_response(
        query="home office deduction",
        role="helpdesk",
        retrieval_response=retrieval_response,
    )

    assert response.outcome is AnswerOutcome.REFUSED
    assert response.evidence.refusal_reason is RefusalReason.CONFLICTING_EVIDENCE
    assert response.state_trace[-1] == "refused"
