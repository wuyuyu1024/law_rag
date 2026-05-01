import pytest

from tax_rag.retrieval.rerank import (
    CrossEncoderReranker,
    DeterministicReranker,
    get_reranker_backend,
    rerank_results,
)
from tax_rag.schemas import (
    ChunkRecord,
    RetrievalMethod,
    RetrievalRequest,
    RetrievalResult,
    ScoreTrace,
    SecurityClassification,
    SourceType,
)


class FakeCrossEncoder:
    def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        return [0.1 if "weaker" in document else 0.9 for _, document in pairs]


def _result(chunk_id: str, text: str) -> RetrievalResult:
    chunk = ChunkRecord(
        chunk_id=chunk_id,
        doc_id=f"doc:{chunk_id}",
        text=text,
        citation_path=f"Demo Law > Artikel {chunk_id}",
        source_type=SourceType.LEGISLATION,
        jurisdiction="NL",
        allowed_roles=("helpdesk",),
        source_path=f"fixtures/{chunk_id}.xml",
        security_classification=SecurityClassification.PUBLIC,
    )
    return RetrievalResult.from_chunk(
        chunk,
        retrieval_method=RetrievalMethod.HYBRID,
        scores=(ScoreTrace(metric="rrf_score", value=0.02, rank=1),),
        metadata={"rank": 1},
    )


def test_get_reranker_backend_defaults_to_deterministic() -> None:
    backend = get_reranker_backend()

    assert isinstance(backend, DeterministicReranker)
    assert backend.name == "deterministic"


def test_get_reranker_backend_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError, match="Unsupported reranker backend"):
        get_reranker_backend("unknown")


def test_deterministic_reranker_adds_backend_and_score_trace() -> None:
    request = RetrievalRequest(query="30 percent ruling employer change", role="helpdesk")
    result = _result(
        "10ed-1",
        "The 30 percent ruling can continue when the employee changes employer during the term.",
    )

    reranked = rerank_results((result,), request, backend=DeterministicReranker())

    score_map = reranked[0].score_map()
    backend_trace = next(score for score in reranked[0].scores if score.metric == "rerank_backend")
    assert reranked[0].metadata["reranked"] is True
    assert "rerank_score" in score_map
    assert backend_trace.metadata == {
        "backend": "deterministic",
        "model": "deterministic-legal-reranker-v1",
    }


def test_cross_encoder_reranker_can_use_injected_model_without_optional_dependency() -> None:
    request = RetrievalRequest(query="which rule applies", role="helpdesk")
    weaker = _result("weaker", "weaker candidate text")
    stronger = _result("stronger", "stronger statutory rule")

    reranked = CrossEncoderReranker(model_name="fake-reranker", model=FakeCrossEncoder()).rerank(
        (weaker, stronger),
        request,
    )

    backend_trace = next(score for score in reranked[0].scores if score.metric == "rerank_backend")
    assert [result.chunk_id for result in reranked] == ["stronger", "weaker"]
    assert reranked[0].score_map()["rerank_score"] == 0.9
    assert backend_trace.metadata == {"backend": "cross_encoder", "model": "fake-reranker"}
