from tax_rag.retrieval import retrieve_lexical
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


def test_retrieve_lexical_matches_exact_ecli_for_authorized_role() -> None:
    authorized_case = _chunk(
        chunk_id="case-authorized",
        source_type=SourceType.CASE_LAW,
        text="Holding on deductibility.",
        citation_path="ECLI:NL:HR:2025:99 > Beslissing > 1",
        allowed_roles=("legal_counsel",),
        security_classification=SecurityClassification.INTERNAL,
        ecli="ECLI:NL:HR:2025:99",
    )
    public_law = _chunk(
        chunk_id="law-public",
        source_type=SourceType.LEGISLATION,
        text="Article text.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 1.2",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="1.2",
    )

    response = retrieve_lexical(
        [authorized_case, public_law],
        RetrievalRequest(query="Ruling ECLI:NL:HR:2025:99", role="legal_counsel", top_k=5),
    )

    assert response.security_stage == "pre_retrieval"
    assert len(response.results) == 1
    assert response.results[0].chunk_id == "case-authorized"
    assert response.results[0].score_map()["ecli_exact_match"] == 300.0
    assert response.results[0].source.ecli == "ECLI:NL:HR:2025:99"


def test_retrieve_lexical_excludes_unauthorized_case_before_matching() -> None:
    restricted_case = _chunk(
        chunk_id="case-restricted",
        source_type=SourceType.CASE_LAW,
        text="Restricted fraud investigation holding.",
        citation_path="ECLI:NL:HR:2025:999 > Beslissing > 1",
        allowed_roles=("inspector", "legal_counsel"),
        security_classification=SecurityClassification.RESTRICTED,
        ecli="ECLI:NL:HR:2025:999",
    )

    response = retrieve_lexical(
        [restricted_case],
        RetrievalRequest(query="ECLI:NL:HR:2025:999", role="helpdesk", top_k=5),
    )

    assert response.results == ()
    assert response.metadata["authorized_candidate_count"] == 0
    assert response.metadata["denied_count"] == 1


def test_retrieve_lexical_ranks_article_paragraph_subparagraph_matches() -> None:
    paragraph_match = _chunk(
        chunk_id="law-3-114-lid-2-a",
        source_type=SourceType.LEGISLATION,
        text="Lid 2 onderdeel a text.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 3.114 > Lid 2 > Onderdeel a.",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="3.114",
        paragraph="2",
        subparagraph="a.",
    )
    article_only = _chunk(
        chunk_id="law-3-114-lid-1",
        source_type=SourceType.LEGISLATION,
        text="Lid 1 text.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 3.114 > Lid 1",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="3.114",
        paragraph="1",
    )

    response = retrieve_lexical(
        [article_only, paragraph_match],
        RetrievalRequest(query="Artikel 3.114 lid 2 onderdeel a", role="helpdesk", top_k=5),
    )

    assert [result.chunk_id for result in response.results] == ["law-3-114-lid-2-a", "law-3-114-lid-1"]
    assert response.results[0].score_map()["article_exact_match"] == 120.0
    assert response.results[0].score_map()["paragraph_exact_match"] == 20.0
    assert response.results[0].score_map()["subparagraph_exact_match"] == 10.0
    assert "article:3.114" in response.results[0].matched_terms


def test_retrieve_lexical_matches_normalized_citation_path() -> None:
    citation_chunk = _chunk(
        chunk_id="law-citation",
        source_type=SourceType.LEGISLATION,
        text="Partner definition.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 1.2",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="1.2",
    )

    response = retrieve_lexical(
        [citation_chunk],
        RetrievalRequest(query="Wet inkomstenbelasting 2001 > Artikel 1.2", role="helpdesk", top_k=5),
    )

    assert len(response.results) == 1
    assert response.results[0].chunk_id == "law-citation"
    assert response.results[0].score_map()["citation_path_exact_match"] == 95.0
    assert response.results[0].source.citation_path == "Wet inkomstenbelasting 2001 > Artikel 1.2"
