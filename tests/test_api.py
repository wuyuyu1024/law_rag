import json
from pathlib import Path

from tax_rag.api.main import QueryRequest, health, run_query
from tax_rag.schemas import AnswerOutcome, ChunkRecord, RetrievalMethod, SecurityClassification, SourceType


def test_health_endpoint_payload() -> None:
    assert health() == {"status": "ok"}


def test_run_query_uses_law_rag_retrieval_service(tmp_path: Path) -> None:
    chunk = ChunkRecord(
        chunk_id="law-10ec-1",
        doc_id="doc:law-10ec-1",
        text="Lid 1. Voor ingekomen werknemers bedraagt de looptijd maximaal vijf jaar.",
        citation_path="Uitvoeringsbesluit loonbelasting 1965 > Artikel 10ec > Lid 1",
        source_type=SourceType.LEGISLATION,
        jurisdiction="NL",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        source_path="fixtures/ublb.xml",
        article="10ec",
        paragraph="1",
        security_classification=SecurityClassification.PUBLIC,
    )
    chunks_path = tmp_path / "chunks.jsonl"
    chunks_path.write_text(f"{json.dumps(chunk.to_dict(), ensure_ascii=False)}\n", encoding="utf-8")

    response = run_query(
        QueryRequest(
            query="Artikel 10ec lid 1",
            role="helpdesk",
            method=RetrievalMethod.LEXICAL,
            chunks_path=str(chunks_path),
        )
    )

    assert response.outcome is AnswerOutcome.ANSWERED
    assert response.citations[0].citation_path == "Uitvoeringsbesluit loonbelasting 1965 > Artikel 10ec > Lid 1"


def test_run_query_can_use_in_memory_semantic_cache(tmp_path: Path) -> None:
    chunk = ChunkRecord(
        chunk_id="wiki-vat-escalation",
        doc_id="doc:wiki-vat",
        text="Helpdesk staff should escalate complex VAT questions to a VAT specialist team.",
        citation_path="VAT Onboarding Module > When To Escalate",
        source_type=SourceType.E_LEARNING,
        jurisdiction="NL",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        source_path="fixtures/vat.json",
        security_classification=SecurityClassification.PUBLIC,
    )
    chunks_path = tmp_path / "chunks.jsonl"
    chunks_path.write_text(f"{json.dumps(chunk.to_dict(), ensure_ascii=False)}\n", encoding="utf-8")
    request = QueryRequest(
        query="when should helpdesk escalate VAT questions",
        role="helpdesk",
        method=RetrievalMethod.HYBRID,
        chunks_path=str(chunks_path),
        cache_backend="in_memory",
    )

    first = run_query(request)
    second = run_query(request)

    assert first.outcome is AnswerOutcome.ANSWERED
    assert first.metadata["semantic_cache"]["stored"] is True
    assert second.metadata["semantic_cache"]["hit"] is True
