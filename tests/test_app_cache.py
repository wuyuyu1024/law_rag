from types import SimpleNamespace

from tax_rag.agent import build_agent_response
from tax_rag.app.cache import CachedCorrectiveRAGAgent
from tax_rag.cache import InMemorySemanticCache
from tax_rag.schemas import (
    AgentResponse,
    ChunkRecord,
    RetrievalMethod,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    ScoreTrace,
    SecurityClassification,
    SourceType,
)


class FakeAgent:
    def __init__(self, response: AgentResponse) -> None:
        self.response = response
        self.calls = 0
        self.retrieval_service = SimpleNamespace(default_method=RetrievalMethod.HYBRID)

    def answer(
        self,
        query: str,
        role: str,
        top_k: int | None = None,
        *,
        method: RetrievalMethod | None = None,
        source_types: tuple[SourceType, ...] = (),
        jurisdiction: str | None = "NL",
        as_of_date: str | None = None,
    ) -> AgentResponse:
        self.calls += 1
        return self.response.model_copy(update={"query": query, "role": role})


def _public_response(query: str = "when should helpdesk escalate VAT questions") -> AgentResponse:
    chunk = ChunkRecord(
        chunk_id="wiki:vat:escalate",
        doc_id="wiki:vat",
        text="Frontline staff should escalate complex VAT questions to a specialist team.",
        citation_path="VAT Onboarding Module > When To Escalate",
        source_type=SourceType.E_LEARNING,
        jurisdiction="NL",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        source_path="fixtures/vat.json",
        security_classification=SecurityClassification.PUBLIC,
    )
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


def test_cached_agent_returns_cached_safe_answer_on_second_call() -> None:
    fake_agent = FakeAgent(_public_response())
    cached_agent = CachedCorrectiveRAGAgent(
        agent=fake_agent,
        cache=InMemorySemanticCache(threshold=0.99),
        cache_backend_name="in_memory",
    )

    first = cached_agent.answer("when should helpdesk escalate VAT questions", "helpdesk")
    second = cached_agent.answer("when should helpdesk escalate VAT questions", "helpdesk")

    assert fake_agent.calls == 1
    assert first.metadata["semantic_cache"] == {
        "enabled": True,
        "backend": "in_memory",
        "hit": False,
        "stored": True,
    }
    assert second.metadata["semantic_cache"] == {
        "enabled": True,
        "backend": "in_memory",
        "hit": True,
        "stored": False,
    }


def test_cached_agent_records_disabled_cache_without_storing() -> None:
    fake_agent = FakeAgent(_public_response())
    cached_agent = CachedCorrectiveRAGAgent(agent=fake_agent)

    response = cached_agent.answer("when should helpdesk escalate VAT questions", "helpdesk")

    assert fake_agent.calls == 1
    assert response.metadata["semantic_cache"] == {
        "enabled": False,
        "backend": None,
        "hit": False,
        "stored": False,
    }
