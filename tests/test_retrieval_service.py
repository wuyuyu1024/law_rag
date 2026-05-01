import json
from pathlib import Path

from tax_rag.retrieval import ResolvedCitation, RetrievalMethod, RetrievalService, resolve_result_citation
from tax_rag.schemas import ChunkRecord, SecurityClassification, SourceType


def _chunk(
    *,
    chunk_id: str,
    source_type: SourceType,
    text: str,
    citation_path: str,
    allowed_roles: tuple[str, ...],
    security_classification: SecurityClassification,
    article: str | None = None,
    ecli: str | None = None,
    valid_from: str | None = None,
    valid_to: str | None = None,
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
        valid_from=valid_from,
        valid_to=valid_to,
        article=article,
        ecli=ecli,
        security_classification=security_classification,
    )


def test_retrieval_service_dispatches_to_hybrid_by_default() -> None:
    service = RetrievalService(
        chunks=[
            _chunk(
                chunk_id="law-home-office",
                source_type=SourceType.LEGISLATION,
                text="Home office expense deductions are limited for mixed private and business use.",
                citation_path="Wet inkomstenbelasting 2001 > Artikel 3.16",
                allowed_roles=("helpdesk", "inspector", "legal_counsel"),
                security_classification=SecurityClassification.PUBLIC,
                article="3.16",
            )
        ]
    )

    response = service.retrieve("Artikel 3.16 home office expenses", "helpdesk")

    assert response.retrieval_method is RetrievalMethod.HYBRID
    assert response.request.top_k == 10
    assert response.results[0].chunk_id == "law-home-office"


def test_retrieval_service_supports_explicit_method_override() -> None:
    service = RetrievalService(
        chunks=[
            _chunk(
                chunk_id="case-ecli",
                source_type=SourceType.CASE_LAW,
                text="Holding on home office expense deductibility.",
                citation_path="ECLI:NL:HR:2025:99 > Beslissing > 1",
                allowed_roles=("legal_counsel",),
                security_classification=SecurityClassification.INTERNAL,
                ecli="ECLI:NL:HR:2025:99",
            )
        ]
    )

    response = service.retrieve(
        "ECLI:NL:HR:2025:99",
        "legal_counsel",
        method=RetrievalMethod.LEXICAL,
    )

    assert response.retrieval_method is RetrievalMethod.LEXICAL
    assert response.results[0].score_map()["ecli_exact_match"] == 300.0


def test_retrieval_service_can_load_chunks_from_jsonl(tmp_path: Path) -> None:
    chunk = _chunk(
        chunk_id="law-citation",
        source_type=SourceType.LEGISLATION,
        text="Partner definition.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 1.2",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="1.2",
    )
    path = tmp_path / "chunks.jsonl"
    path.write_text(f"{json.dumps(chunk.to_dict(), ensure_ascii=False)}\n", encoding="utf-8")

    service = RetrievalService.from_jsonl(str(path), default_method=RetrievalMethod.LEXICAL)
    response = service.retrieve("Wet inkomstenbelasting 2001 > Artikel 1.2", "helpdesk")

    assert response.retrieval_method is RetrievalMethod.LEXICAL
    assert response.results[0].chunk_id == "law-citation"


def test_retrieval_service_filters_chunks_by_as_of_date() -> None:
    service = RetrievalService(
        chunks=[
            _chunk(
                chunk_id="law-article-old",
                source_type=SourceType.LEGISLATION,
                text="Old version of the rule.",
                citation_path="Demo Tax Act > Artikel 9.1",
                allowed_roles=("helpdesk", "inspector", "legal_counsel"),
                security_classification=SecurityClassification.PUBLIC,
                article="9.1",
                valid_from="2020-01-01",
                valid_to="2024-12-31",
            ),
            _chunk(
                chunk_id="law-article-current",
                source_type=SourceType.LEGISLATION,
                text="Current version of the rule.",
                citation_path="Demo Tax Act > Artikel 9.1",
                allowed_roles=("helpdesk", "inspector", "legal_counsel"),
                security_classification=SecurityClassification.PUBLIC,
                article="9.1",
                valid_from="2025-01-01",
            ),
        ],
        default_method=RetrievalMethod.LEXICAL,
    )

    current = service.retrieve("Artikel 9.1 as of 2026-01-01", "helpdesk")
    historical = service.retrieve("Artikel 9.1", "helpdesk", as_of_date="2024-06-01")

    assert current.request.as_of_date == "2026-01-01"
    assert current.results[0].chunk_id == "law-article-current"
    assert current.metadata["validity_filtered_count"] == 1
    assert historical.results[0].chunk_id == "law-article-old"


def test_resolve_result_citation_preserves_stable_linkage() -> None:
    service = RetrievalService(
        chunks=[
            _chunk(
                chunk_id="case-ecli",
                source_type=SourceType.CASE_LAW,
                text="Holding on home office expense deductibility.",
                citation_path="ECLI:NL:HR:2025:99 > Beslissing > 1",
                allowed_roles=("legal_counsel",),
                security_classification=SecurityClassification.INTERNAL,
                ecli="ECLI:NL:HR:2025:99",
            )
        ]
    )

    response = service.retrieve("ECLI:NL:HR:2025:99", "legal_counsel", method=RetrievalMethod.LEXICAL)
    citation = resolve_result_citation(response.results[0])

    assert citation == ResolvedCitation(
        label="ECLI:NL:HR:2025:99",
        source_type=SourceType.CASE_LAW,
        source_path="fixtures/case-ecli.xml",
        citation_path="ECLI:NL:HR:2025:99 > Beslissing > 1",
        doc_id="doc:case-ecli",
        chunk_id="case-ecli",
    )
