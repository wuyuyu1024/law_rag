"""App-level answer caching for safe semantic-cache integration."""

from __future__ import annotations

from dataclasses import dataclass

from tax_rag.agent import CorrectiveRAGAgent
from tax_rag.cache import (
    InMemorySemanticCache,
    RedisSemanticCache,
    SemanticCacheBackend,
    build_semantic_cache_key,
)
from tax_rag.common import DEFAULT_CONFIG
from tax_rag.retrieval import RetrievalMethod
from tax_rag.retrieval.common import infer_as_of_date
from tax_rag.schemas import AgentResponse, SourceType

DEFAULT_CORPUS_VERSION = "demo-corpus-v1"
DEFAULT_GENERATOR_VERSION = "deterministic-agent-v1"


def semantic_cache_from_config(backend: str | None = None) -> SemanticCacheBackend | None:
    backend_name = (backend or DEFAULT_CONFIG.cache.backend).strip().lower()
    if backend is None and not DEFAULT_CONFIG.cache.enabled:
        return None
    if backend_name in {"none", "disabled", "off"}:
        return None
    if backend_name in {"in_memory", "memory"}:
        return InMemorySemanticCache()
    if backend_name == "redis":
        return RedisSemanticCache()
    raise ValueError(f"Unsupported semantic cache backend: {backend_name}")


def _source_scope(source_types: tuple[SourceType, ...]) -> tuple[str, ...]:
    if not source_types:
        return ("all_authorized_sources",)
    return tuple(source_type.value for source_type in source_types)


def _retrieval_version(method: RetrievalMethod) -> str:
    return (
        f"{method.value}:"
        f"dense={DEFAULT_CONFIG.retrieval.dense_model}:"
        f"reranker={DEFAULT_CONFIG.reranking.backend}:"
        f"reranker_model={DEFAULT_CONFIG.reranking.model}"
    )


def _cache_metadata(*, enabled: bool, backend: str | None, hit: bool, stored: bool = False) -> dict[str, object]:
    return {
        "enabled": enabled,
        "backend": backend,
        "hit": hit,
        "stored": stored,
    }


@dataclass
class CachedCorrectiveRAGAgent:
    agent: CorrectiveRAGAgent
    cache: SemanticCacheBackend | None = None
    cache_backend_name: str | None = None
    corpus_version: str = DEFAULT_CORPUS_VERSION
    generator_version: str = DEFAULT_GENERATOR_VERSION

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
        effective_as_of_date = as_of_date or infer_as_of_date(query)
        retrieval_method = method or self.agent.retrieval_service.default_method
        cache_key = build_semantic_cache_key(
            role=role,
            jurisdiction=jurisdiction or "unspecified",
            corpus_version=self.corpus_version,
            retrieval_version=_retrieval_version(retrieval_method),
            generator_version=self.generator_version,
            source_scope=(*_source_scope(source_types), f"as_of:{effective_as_of_date or 'current'}"),
        )
        if self.cache is not None:
            cached = self.cache.get(query, cache_key)
            if cached is not None:
                return cached.model_copy(
                    update={
                        "metadata": {
                            **cached.metadata,
                            "semantic_cache": _cache_metadata(
                                enabled=True,
                                backend=self.cache_backend_name,
                                hit=True,
                            ),
                        }
                    }
                )

        response = self.agent.answer(
            query,
            role,
            top_k=top_k,
            method=method,
            source_types=source_types,
            jurisdiction=jurisdiction,
            as_of_date=effective_as_of_date,
        )
        stored = self.cache.set(response, cache_key) if self.cache is not None else False
        return response.model_copy(
            update={
                "metadata": {
                    **response.metadata,
                    "semantic_cache": _cache_metadata(
                        enabled=self.cache is not None,
                        backend=self.cache_backend_name,
                        hit=False,
                        stored=stored,
                    ),
                }
            }
        )
