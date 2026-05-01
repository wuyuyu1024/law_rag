"""Role-aware semantic cache policy for low-risk demo answers."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from time import time
from typing import Protocol, cast

from tax_rag.common import DEFAULT_CONFIG
from tax_rag.common.dense import embed_text
from tax_rag.schemas import AgentResponse, AnswerOutcome, EvidenceGrade
from tax_rag.schemas.document import SchemaModel

_EXACT_IDENTIFIER_PATTERN = re.compile(
    r"\b(?:ecli:|artikel|article|art\.?|lid|paragraph)\b",
    re.IGNORECASE,
)


class SemanticCacheKey(SchemaModel):
    role: str
    jurisdiction: str
    corpus_version: str
    retrieval_version: str
    generator_version: str
    source_scope: tuple[str, ...] = ()


class RedisCacheClient(Protocol):
    def get(self, name: str) -> bytes | str | None: ...

    def setex(self, name: str, time: int, value: str) -> object: ...

    def delete(self, *names: str) -> object: ...


@dataclass(frozen=True)
class _CacheEntry:
    query: str
    vector: tuple[float, ...]
    response: AgentResponse
    expires_at: float


def can_cache_response(response: AgentResponse) -> bool:
    if response.outcome is not AnswerOutcome.ANSWERED:
        return False
    if response.evidence.grade is not EvidenceGrade.RELEVANT:
        return False
    if _EXACT_IDENTIFIER_PATTERN.search(response.query):
        return False
    classifications = response.metadata.get("source_security_classifications", ())
    if not isinstance(classifications, (list, tuple)) or not classifications:
        return False
    return set(classifications) == {"public"}


class InMemorySemanticCache:
    """Conservative semantic cache for public, relevant, non-exact answers."""

    def __init__(
        self,
        *,
        threshold: float = DEFAULT_CONFIG.cache.semantic_similarity_threshold,
        ttl_seconds: int = DEFAULT_CONFIG.cache.semantic_cache_ttl_seconds,
        dimensions: int = DEFAULT_CONFIG.retrieval.dense_dimensions,
    ) -> None:
        self.threshold = threshold
        self.ttl_seconds = ttl_seconds
        self.dimensions = dimensions
        self._entries: dict[SemanticCacheKey, list[_CacheEntry]] = {}

    def get(self, query: str, key: SemanticCacheKey) -> AgentResponse | None:
        vector = self._embed(query)
        now = time()
        live_entries = [entry for entry in self._entries.get(key, []) if entry.expires_at > now]
        self._entries[key] = live_entries
        for entry in live_entries:
            if _cosine(vector, entry.vector) >= self.threshold:
                return entry.response
        return None

    def set(self, response: AgentResponse, key: SemanticCacheKey) -> bool:
        if not self.can_cache(response):
            return False
        self._entries.setdefault(key, []).append(
            _CacheEntry(
                query=response.query,
                vector=self._embed(response.query),
                response=response,
                expires_at=time() + self.ttl_seconds,
            )
        )
        return True

    def can_cache(self, response: AgentResponse) -> bool:
        return can_cache_response(response)

    def _embed(self, value: str) -> tuple[float, ...]:
        return tuple(embed_text(value, dimensions=self.dimensions))


class RedisSemanticCache:
    """Redis-backed semantic cache using the same conservative policy as memory mode."""

    def __init__(
        self,
        *,
        redis_url: str = DEFAULT_CONFIG.cache.redis_url,
        client: RedisCacheClient | None = None,
        namespace: str = "tax_rag:semantic_cache",
        threshold: float = DEFAULT_CONFIG.cache.semantic_similarity_threshold,
        ttl_seconds: int = DEFAULT_CONFIG.cache.semantic_cache_ttl_seconds,
        dimensions: int = DEFAULT_CONFIG.retrieval.dense_dimensions,
    ) -> None:
        self.threshold = threshold
        self.ttl_seconds = ttl_seconds
        self.dimensions = dimensions
        self.namespace = namespace.rstrip(":")
        self._client = client or self._client_from_url(redis_url)

    def get(self, query: str, key: SemanticCacheKey) -> AgentResponse | None:
        vector = self._embed(query)
        entries = self._live_entries(key)
        if not entries:
            return None
        for entry in entries:
            if _cosine(vector, entry.vector) >= self.threshold:
                return entry.response
        return None

    def set(self, response: AgentResponse, key: SemanticCacheKey) -> bool:
        if not self.can_cache(response):
            return False
        entries = self._live_entries(key)
        entries.append(
            _CacheEntry(
                query=response.query,
                vector=self._embed(response.query),
                response=response,
                expires_at=time() + self.ttl_seconds,
            )
        )
        self._store_entries(key, entries)
        return True

    def can_cache(self, response: AgentResponse) -> bool:
        return can_cache_response(response)

    def clear_namespace(self, key: SemanticCacheKey) -> None:
        self._client.delete(self._redis_key(key))

    def _embed(self, value: str) -> tuple[float, ...]:
        return tuple(embed_text(value, dimensions=self.dimensions))

    def _live_entries(self, key: SemanticCacheKey) -> list[_CacheEntry]:
        raw = self._client.get(self._redis_key(key))
        if raw is None:
            return []
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        entries = _deserialize_entries(raw)
        now = time()
        live_entries = [entry for entry in entries if entry.expires_at > now]
        if len(live_entries) != len(entries):
            self._store_entries(key, live_entries)
        return live_entries

    def _store_entries(self, key: SemanticCacheKey, entries: list[_CacheEntry]) -> None:
        if not entries:
            self._client.delete(self._redis_key(key))
            return
        self._client.setex(self._redis_key(key), self.ttl_seconds, _serialize_entries(entries))

    def _redis_key(self, key: SemanticCacheKey) -> str:
        digest = hashlib.sha256(key.to_json().encode("utf-8")).hexdigest()
        return f"{self.namespace}:{digest}"

    @staticmethod
    def _client_from_url(redis_url: str) -> RedisCacheClient:
        from redis import Redis

        return cast(RedisCacheClient, Redis.from_url(redis_url, decode_responses=True))


def build_semantic_cache_key(
    *,
    role: str,
    jurisdiction: str = "NL",
    corpus_version: str,
    retrieval_version: str,
    generator_version: str,
    source_scope: tuple[str, ...] = (),
) -> SemanticCacheKey:
    return SemanticCacheKey(
        role=role,
        jurisdiction=jurisdiction,
        corpus_version=corpus_version,
        retrieval_version=retrieval_version,
        generator_version=generator_version,
        source_scope=tuple(sorted(source_scope)),
    )


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _serialize_entries(entries: list[_CacheEntry]) -> str:
    payload = [
        {
            "query": entry.query,
            "vector": list(entry.vector),
            "response": entry.response.to_dict(),
            "expires_at": entry.expires_at,
        }
        for entry in entries
    ]
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _deserialize_entries(raw: str) -> list[_CacheEntry]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []

    entries: list[_CacheEntry] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        query = item.get("query")
        vector = item.get("vector")
        response = item.get("response")
        expires_at = item.get("expires_at")
        if not isinstance(query, str) or not isinstance(vector, list) or not isinstance(response, dict):
            continue
        if not isinstance(expires_at, int | float):
            continue
        try:
            vector_tuple = tuple(float(value) for value in vector)
            response_model = AgentResponse.model_validate(response)
        except (TypeError, ValueError):
            continue
        entries.append(
            _CacheEntry(
                query=query,
                vector=vector_tuple,
                response=response_model,
                expires_at=float(expires_at),
            )
        )
    return entries
