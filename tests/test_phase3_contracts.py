import pytest

from tax_rag.schemas import (
    ChunkRecord,
    RetrievalMethod,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    ScoreTrace,
    SecurityClassification,
    SourceReference,
    SourceType,
)
from tax_rag.security import (
    DEFAULT_RETRIEVAL_SECURITY_CONTRACT,
    ProtectedRetrievalSurface,
    RetrievalEnforcementStage,
    RetrievalSecurityContract,
    validate_retrieval_enforcement_stage,
)


def _sample_chunk() -> ChunkRecord:
    return ChunkRecord(
        chunk_id="case:hr:2023:123:section:holding:1",
        doc_id="case:hr:2023:123",
        text="Holding 1 The deduction is denied for the stated period.",
        citation_path="ECLI:NL:HR:2023:123 > Beslissing > 1",
        source_type=SourceType.CASE_LAW,
        jurisdiction="NL",
        allowed_roles=("inspector", "legal_counsel"),
        source_path="data/raw/cases/ecli_nl_hr_2023_123.xml",
        ecli="ECLI:NL:HR:2023:123",
        court="Hoge Raad",
        decision_date="2023-03-01",
        section_type="holding",
        security_classification=SecurityClassification.INTERNAL,
    )


def test_retrieval_security_contract_locks_enforcement_to_pre_retrieval() -> None:
    assert DEFAULT_RETRIEVAL_SECURITY_CONTRACT.enforcement_stage is RetrievalEnforcementStage.PRE_RETRIEVAL
    assert ProtectedRetrievalSurface.LEXICAL in DEFAULT_RETRIEVAL_SECURITY_CONTRACT.protected_surfaces
    assert ProtectedRetrievalSurface.DENSE in DEFAULT_RETRIEVAL_SECURITY_CONTRACT.protected_surfaces
    assert ProtectedRetrievalSurface.RERANKING in DEFAULT_RETRIEVAL_SECURITY_CONTRACT.protected_surfaces

    with pytest.raises(ValueError):
        validate_retrieval_enforcement_stage("post_retrieval")

    with pytest.raises(ValueError):
        RetrievalSecurityContract(enforcement_stage="pre_rank")  # type: ignore[arg-type]


def test_retrieval_request_requires_query_role_and_positive_top_k() -> None:
    request = RetrievalRequest(query="ECLI:NL:HR:2023:123", role="legal_counsel", top_k=5)

    assert request.top_k == 5

    with pytest.raises(ValueError):
        RetrievalRequest(query=" ", role="legal_counsel")

    with pytest.raises(ValueError):
        RetrievalRequest(query="box 1 rate", role=" ")

    with pytest.raises(ValueError):
        RetrievalRequest(query="box 1 rate", role="helpdesk", top_k=0)


def test_source_reference_and_retrieval_result_round_trip_with_inspectable_scores() -> None:
    chunk = _sample_chunk()
    result = RetrievalResult.from_chunk(
        chunk,
        retrieval_method=RetrievalMethod.HYBRID,
        scores=(
            ScoreTrace(metric="lexical_score", value=12.0, rank=1),
            ScoreTrace(metric="dense_score", value=0.82, rank=3),
            ScoreTrace(metric="rrf_score", value=0.03226, rank=1),
        ),
        matched_terms=("ecli:nl:hr:2023:123",),
        metadata={"authorized": True},
    )

    assert result.chunk_id == chunk.chunk_id
    assert result.doc_id == chunk.doc_id
    assert result.score_map()["rrf_score"] == pytest.approx(0.03226)
    assert result.source.ecli == "ECLI:NL:HR:2023:123"

    payload = result.to_dict()
    restored = RetrievalResult.from_dict(payload)

    assert restored == result


def test_retrieval_response_keeps_request_results_and_security_stage() -> None:
    chunk = _sample_chunk()
    result = RetrievalResult.from_chunk(
        chunk,
        retrieval_method=RetrievalMethod.LEXICAL,
        scores=(ScoreTrace(metric="lexical_score", value=7.5, rank=1),),
    )
    response = RetrievalResponse(
        request=RetrievalRequest(query="Article 3.114 lid 2", role="inspector", top_k=3),
        retrieval_method=RetrievalMethod.LEXICAL,
        results=(result,),
        security_stage=RetrievalEnforcementStage.PRE_RETRIEVAL.value,
        metadata={"candidate_count": 1},
    )

    serialized = response.to_dict()

    assert serialized["security_stage"] == "pre_retrieval"
    assert serialized["results"][0]["source"]["chunk_id"] == chunk.chunk_id
    assert serialized["results"][0]["scores"][0]["metric"] == "lexical_score"

    restored = RetrievalResponse.from_dict(serialized)

    assert restored == response
    assert isinstance(restored.results[0].source, SourceReference)
