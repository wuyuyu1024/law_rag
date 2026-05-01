"""Role-aware semantic cache policy for low-risk demo answers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from time import time

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


@dataclass(frozen=True)
class _CacheEntry:
    query: str
    vector: tuple[float, ...]
    response: AgentResponse
    expires_at: float


class InMemorySemanticCache:
    """Conservative semantic cache for public, relevant, non-exact answers."""

    def __init__(
        self,
        *,
        threshold: float = DEFAULT_CONFIG.cache.semantic_similarity_threshold,
        ttl_seconds: int = 86_400,
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

    def _embed(self, value: str) -> tuple[float, ...]:
        return tuple(embed_text(value, dimensions=self.dimensions))


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
