from tax_rag.app import format_agent_response
from tax_rag.schemas import (
    AgentResponse,
    AnswerCitation,
    AnswerOutcome,
    EvidenceAssessment,
    EvidenceGrade,
    RefusalReason,
    RetrievalMethod,
    SourceType,
)


def test_format_agent_response_includes_answer_citations_state_trace_and_timings() -> None:
    response = AgentResponse(
        query="Artikel 3.114 lid 2",
        role="helpdesk",
        outcome=AnswerOutcome.ANSWERED,
        answer_text="Primary evidence from Wet inkomstenbelasting 2001 > Artikel 3.114 > Lid 2: ...",
        citations=(
            AnswerCitation(
                label="Wet inkomstenbelasting 2001 > Artikel 3.114 > Lid 2",
                source_type=SourceType.LEGISLATION,
                source_path="fixtures/law.xml",
                citation_path="Wet inkomstenbelasting 2001 > Artikel 3.114 > Lid 2",
                doc_id="doc:law-home-office",
                chunk_id="law-home-office",
            ),
        ),
        evidence=EvidenceAssessment(
            grade=EvidenceGrade.RELEVANT,
            explanation="Top result is clearly relevant.",
            result_count=1,
        ),
        retrieval_method=RetrievalMethod.HYBRID,
        state_trace=("understood", "retrieved", "graded", "answered"),
        metadata={
            "transform_plan": {"strategy": "structured_identifier", "transformed_queries": ["Artikel 3.114 lid 2"]},
            "retrieval_metadata": {
                "authorized_candidate_count": 10,
                "denied_count": 2,
                "total_chunk_count": 50,
                "timings_ms": {
                    "request_scoping_ms": 0.25,
                    "security_filter_ms": 1.50,
                    "lexical_retrieval_ms": 12.0,
                    "dense_retrieval_ms": 40.0,
                    "fusion_ms": 0.9,
                    "reranking_ms": 0.0,
                    "retrieval_total_ms": 54.65,
                },
            },
        },
    )

    rendered = format_agent_response(response)

    assert "outcome: answered" in rendered
    assert "response:" in rendered
    assert "citations:" in rendered
    assert "state_trace:" in rendered
    assert "understood -> retrieved -> graded -> answered" in rendered
    assert "retrieval:" in rendered
    assert "- dense_retrieval_ms: 40.000 ms" in rendered


def test_format_agent_response_includes_refusal_reason() -> None:
    response = AgentResponse(
        query="fraud guidance",
        role="helpdesk",
        outcome=AnswerOutcome.REFUSED,
        evidence=EvidenceAssessment(
            grade=EvidenceGrade.IRRELEVANT,
            explanation="No authorized source was available for this role.",
            result_count=0,
            refusal_reason=RefusalReason.NO_AUTHORIZED_SOURCE,
        ),
        retrieval_method=RetrievalMethod.DENSE,
        state_trace=("understood", "retrieved", "graded", "refused"),
    )

    rendered = format_agent_response(response)

    assert "outcome: refused" in rendered
    assert "refusal_reason: no_authorized_source" in rendered
    assert "No authorized source was available for this role." in rendered
