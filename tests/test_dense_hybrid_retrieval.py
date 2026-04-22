import pytest

from tax_rag.retrieval import retrieve_dense, retrieve_hybrid
from tax_rag.schemas import ChunkRecord, RetrievalRequest, SecurityClassification, SourceType


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
    subparagraph: str | None = None,
    ecli: str | None = None,
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
        subparagraph=subparagraph,
        ecli=ecli,
        security_classification=security_classification,
    )


def test_retrieve_dense_ranks_semantically_closest_authorized_chunk() -> None:
    relevant = _chunk(
        chunk_id="law-home-office",
        source_type=SourceType.LEGISLATION,
        text="Home office expense deductions are limited for mixed private and business use.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 3.16",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="3.16",
    )
    unrelated = _chunk(
        chunk_id="law-partner",
        source_type=SourceType.LEGISLATION,
        text="Partner definitions for tax filing purposes.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 1.2",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="1.2",
    )

    response = retrieve_dense(
        [unrelated, relevant],
        RetrievalRequest(query="deductibility of home office expenses", role="helpdesk", top_k=5),
    )

    assert response.security_stage == "pre_retrieval"
    assert response.results[0].chunk_id == "law-home-office"
    assert response.results[0].score_map()["dense_score"] > response.results[1].score_map()["dense_score"]


def test_retrieve_dense_excludes_unauthorized_candidates_before_similarity_scoring() -> None:
    restricted = _chunk(
        chunk_id="restricted-fraud-manual",
        source_type=SourceType.INTERNAL_POLICY,
        text="Home office deduction fraud indicators and investigation steps.",
        citation_path="Fraud Manual > Home Office",
        allowed_roles=("inspector", "legal_counsel"),
        security_classification=SecurityClassification.RESTRICTED,
    )
    public = _chunk(
        chunk_id="public-guidance",
        source_type=SourceType.E_LEARNING,
        text="General guidance on deductible workplace costs.",
        citation_path="VAT Onboarding > Deductions",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
    )

    response = retrieve_dense(
        [restricted, public],
        RetrievalRequest(query="home office deduction guidance", role="helpdesk", top_k=5),
    )

    assert [result.chunk_id for result in response.results] == ["public-guidance"]
    assert response.metadata["denied_count"] == 1
    assert response.metadata["authorized_candidate_count"] == 1


def test_retrieve_hybrid_fuses_lexical_and_dense_results_with_rrf() -> None:
    strong_both = _chunk(
        chunk_id="law-home-office-3-16",
        source_type=SourceType.LEGISLATION,
        text="Home office expense deductions are limited for mixed private and business use.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 3.16",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="3.16",
    )
    lexical_only = _chunk(
        chunk_id="law-home-office-3-17",
        source_type=SourceType.LEGISLATION,
        text="Specific article reference without relevant semantics.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 3.16 > Lid 2",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="3.16",
        paragraph="2",
    )
    dense_only = _chunk(
        chunk_id="law-workspace-semantics",
        source_type=SourceType.LEGISLATION,
        text="Workspace expenses and home office costs are deductible only in limited tax scenarios.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 3.200",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="3.200",
    )

    response = retrieve_hybrid(
        [lexical_only, strong_both, dense_only],
        RetrievalRequest(query="Artikel 3.16 home office expenses", role="helpdesk", top_k=3),
    )

    assert response.retrieval_method.value == "hybrid"
    assert response.results[0].chunk_id == "law-home-office-3-16"
    assert response.metadata["fusion_strategy"] == "rrf"
    assert response.results[0].score_map()["rrf_score"] > response.results[1].score_map()["rrf_score"]
    assert "article:3.16" in response.results[0].matched_terms


def test_retrieve_hybrid_returns_inspectable_stage_scores() -> None:
    chunk = _chunk(
        chunk_id="case-ecli-hybrid",
        source_type=SourceType.CASE_LAW,
        text="Holding on home office expense deductibility.",
        citation_path="ECLI:NL:HR:2025:99 > Beslissing > 1",
        allowed_roles=("legal_counsel",),
        security_classification=SecurityClassification.INTERNAL,
        ecli="ECLI:NL:HR:2025:99",
    )

    response = retrieve_hybrid(
        [chunk],
        RetrievalRequest(query="ECLI:NL:HR:2025:99 home office", role="legal_counsel", top_k=3),
    )

    score_map = response.results[0].score_map()

    assert score_map["ecli_exact_match"] == 300.0
    assert score_map["dense_score"] > 0.0
    assert score_map["rrf_lexical"] == pytest.approx(1 / 61)
    assert score_map["rrf_dense"] == pytest.approx(1 / 61)
    assert score_map["rrf_score"] == pytest.approx(2 / 61)
