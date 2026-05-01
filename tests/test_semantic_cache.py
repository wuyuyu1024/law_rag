from tax_rag.agent import build_agent_response
from tax_rag.cache import InMemorySemanticCache, RedisSemanticCache, build_semantic_cache_key
from tax_rag.schemas import (
    AgentResponse,
    AnswerOutcome,
    ChunkRecord,
    EvidenceGrade,
    RetrievalMethod,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    ScoreTrace,
    SecurityClassification,
    SourceType,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.deleted: list[str] = []

    def get(self, name: str) -> str | None:
        return self.values.get(name)

    def setex(self, name: str, time: int, value: str) -> object:
        self.values[name] = value
        self.ttls[name] = time
        return True

    def delete(self, *names: str) -> object:
        for name in names:
            self.values.pop(name, None)
            self.ttls.pop(name, None)
            self.deleted.append(name)
        return len(names)


def _chunk(
    *,
    chunk_id: str,
    security_classification: SecurityClassification = SecurityClassification.PUBLIC,
) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=chunk_id,
        doc_id=f"doc:{chunk_id}",
        text="Public guidance says home office costs require authoritative evidence.",
        citation_path="Public Tax Guidance > Home Office",
        source_type=SourceType.E_LEARNING,
        jurisdiction="NL",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        source_path=f"fixtures/{chunk_id}.json",
        security_classification=security_classification,
    )


def _response(
    *,
    query: str = "home office cost evidence",
    security_classification: SecurityClassification = SecurityClassification.PUBLIC,
) -> AgentResponse:
    chunk = _chunk(chunk_id="public-home-office", security_classification=security_classification)
    retrieval_response = RetrievalResponse(
        request=RetrievalRequest(query=query, role="helpdesk"),
        retrieval_method=RetrievalMethod.HYBRID,
        results=(
            RetrievalResult.from_chunk(
                chunk,
                retrieval_method=RetrievalMethod.HYBRID,
                scores=(ScoreTrace(metric="rerank_score", value=0.8, rank=1),),
            ),
        ),
        security_stage="pre_retrieval",
    )
    return build_agent_response(query=query, role="helpdesk", retrieval_response=retrieval_response)


def test_semantic_cache_stores_public_relevant_non_exact_answer_by_namespace() -> None:
    cache = InMemorySemanticCache(threshold=0.99)
    key = build_semantic_cache_key(
        role="helpdesk",
        corpus_version="demo-v1",
        retrieval_version="hybrid-v1",
        generator_version="local-v1",
        source_scope=("public",),
    )
    other_role_key = build_semantic_cache_key(
        role="inspector",
        corpus_version="demo-v1",
        retrieval_version="hybrid-v1",
        generator_version="local-v1",
        source_scope=("public",),
    )
    response = _response()

    assert response.outcome is AnswerOutcome.ANSWERED
    assert response.evidence.grade is EvidenceGrade.RELEVANT
    assert cache.set(response, key)
    assert cache.get(response.query, key) == response
    assert cache.get(response.query, other_role_key) is None


def test_semantic_cache_rejects_exact_identifier_queries() -> None:
    cache = InMemorySemanticCache()
    key = build_semantic_cache_key(
        role="helpdesk",
        corpus_version="demo-v1",
        retrieval_version="hybrid-v1",
        generator_version="local-v1",
    )
    response = _response(query="Artikel 10ec lid 1")

    assert not cache.set(response, key)
    assert cache.get(response.query, key) is None


def test_semantic_cache_rejects_non_public_sources() -> None:
    cache = InMemorySemanticCache()
    key = build_semantic_cache_key(
        role="helpdesk",
        corpus_version="demo-v1",
        retrieval_version="hybrid-v1",
        generator_version="local-v1",
    )
    response = _response(security_classification=SecurityClassification.INTERNAL)

    assert not cache.set(response, key)


def test_redis_semantic_cache_stores_serialized_answers_by_namespace() -> None:
    redis = FakeRedis()
    cache = RedisSemanticCache(client=redis, threshold=0.99, ttl_seconds=3600)
    key = build_semantic_cache_key(
        role="helpdesk",
        corpus_version="demo-v1",
        retrieval_version="hybrid-v1",
        generator_version="local-v1",
        source_scope=("public",),
    )
    other_role_key = build_semantic_cache_key(
        role="inspector",
        corpus_version="demo-v1",
        retrieval_version="hybrid-v1",
        generator_version="local-v1",
        source_scope=("public",),
    )
    response = _response()

    assert cache.set(response, key)
    assert redis.ttls
    cached = cache.get(response.query, key)
    assert cached is not None
    assert cached.answer_text == response.answer_text
    assert cached.citations == response.citations
    assert cached.outcome is response.outcome
    assert cache.get(response.query, other_role_key) is None


def test_redis_semantic_cache_rejects_unsafe_answers_without_writing() -> None:
    redis = FakeRedis()
    cache = RedisSemanticCache(client=redis)
    key = build_semantic_cache_key(
        role="helpdesk",
        corpus_version="demo-v1",
        retrieval_version="hybrid-v1",
        generator_version="local-v1",
    )
    response = _response(query="ECLI:NL:HR:2025:99")

    assert not cache.set(response, key)
    assert redis.values == {}
