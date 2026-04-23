from tax_rag.agent import CorrectiveRAGAgent, transform_query
from tax_rag.schemas import (
    AgentState,
    AnswerOutcome,
    ChunkRecord,
    QueryTransformStrategy,
    RefusalReason,
    RetrievalMethod,
    SecurityClassification,
    SourceType,
)
from tax_rag.retrieval import RetrievalService


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


def test_transform_query_decomposes_multi_part_query() -> None:
    plan = transform_query("What does Artikel 3.114 lid 2 say and what is ECLI:NL:HR:2025:99?")

    assert plan.strategy is QueryTransformStrategy.DECOMPOSITION
    assert len(plan.transformed_queries) == 2


def test_corrective_rag_agent_retries_with_structured_identifier() -> None:
    service = RetrievalService(
        chunks=[
            _chunk(
                chunk_id="case-ecli",
                source_type=SourceType.CASE_LAW,
                text="Holding on deductibility.",
                citation_path="ECLI:NL:HR:2025:99 > Beslissing > 1",
                allowed_roles=("legal_counsel",),
                security_classification=SecurityClassification.INTERNAL,
                ecli="ECLI:NL:HR:2025:99",
                decision_date="2025-01-17",
            )
        ],
        default_method=RetrievalMethod.DENSE,
    )
    agent = CorrectiveRAGAgent(retrieval_service=service)

    response = agent.answer("Can you explain ruling ECLI:NL:HR:2025:99 for me?", "legal_counsel")

    assert response.outcome is AnswerOutcome.ANSWERED
    assert AgentState.TRANSFORMED.value in response.state_trace
    assert response.metadata["transform_plan"]["strategy"] == QueryTransformStrategy.STRUCTURED_IDENTIFIER.value
    assert response.citations[0].label == "ECLI:NL:HR:2025:99"
    trace = response.metadata["execution_trace"]
    assert any(event["event"] == "retrieval_completed" for event in trace)
    assert trace[-1]["event"] == "response_finalized"


def test_corrective_rag_agent_answers_when_all_subqueries_are_supported() -> None:
    service = RetrievalService(
        chunks=[
            _chunk(
                chunk_id="law-home-office",
                source_type=SourceType.LEGISLATION,
                text="Lid 2 provides the rule for home office deductions.",
                citation_path="Wet inkomstenbelasting 2001 > Artikel 3.114 > Lid 2",
                allowed_roles=("helpdesk", "inspector", "legal_counsel"),
                security_classification=SecurityClassification.PUBLIC,
                article="3.114",
                paragraph="2",
            ),
            _chunk(
                chunk_id="case-ecli",
                source_type=SourceType.CASE_LAW,
                text="The Hoge Raad clarified the same deduction rule.",
                citation_path="ECLI:NL:HR:2025:99 > Beslissing > 1",
                allowed_roles=("helpdesk", "inspector", "legal_counsel"),
                security_classification=SecurityClassification.PUBLIC,
                ecli="ECLI:NL:HR:2025:99",
                decision_date="2025-01-17",
            ),
        ],
        default_method=RetrievalMethod.HYBRID,
    )
    agent = CorrectiveRAGAgent(retrieval_service=service)

    response = agent.answer(
        "What does Artikel 3.114 lid 2 say and what is ECLI:NL:HR:2025:99?",
        "helpdesk",
    )

    assert response.outcome is AnswerOutcome.ANSWERED
    assert response.state_trace[0] == AgentState.UNDERSTOOD.value
    assert AgentState.TRANSFORMED.value in response.state_trace
    assert response.metadata["subqueries"][0]["evidence_grade"] == "relevant"
    assert "For 'What does Artikel 3.114 lid 2 say'" in response.answer_text
    assert response.metadata["execution_trace"][1]["event"] == "query_transform_planned"


def test_corrective_rag_agent_refuses_when_a_subquery_lacks_evidence() -> None:
    service = RetrievalService(
        chunks=[
            _chunk(
                chunk_id="law-home-office",
                source_type=SourceType.LEGISLATION,
                text="Lid 2 provides the rule for home office deductions.",
                citation_path="Wet inkomstenbelasting 2001 > Artikel 3.114 > Lid 2",
                allowed_roles=("helpdesk", "inspector", "legal_counsel"),
                security_classification=SecurityClassification.PUBLIC,
                article="3.114",
                paragraph="2",
            )
        ],
        default_method=RetrievalMethod.HYBRID,
    )
    agent = CorrectiveRAGAgent(retrieval_service=service)

    response = agent.answer(
        "What does Artikel 3.114 lid 2 say and what is ECLI:NL:HR:2025:99?",
        "helpdesk",
    )

    assert response.outcome is AnswerOutcome.REFUSED
    assert response.evidence.refusal_reason in {RefusalReason.INSUFFICIENT_EVIDENCE, RefusalReason.NO_AUTHORIZED_SOURCE}
    assert response.state_trace[-1] == AgentState.REFUSED.value
