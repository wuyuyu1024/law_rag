"""Deterministic dense-style retrieval over RBAC-authorized chunk candidates."""

from __future__ import annotations

import hashlib
import math
import re

from tax_rag.common import DEFAULT_CONFIG
from tax_rag.retrieval.common import request_allows_chunk
from tax_rag.schemas import (
    ChunkRecord,
    RetrievalMethod,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    ScoreTrace,
)
from tax_rag.security import (
    DEFAULT_RETRIEVAL_SECURITY_CONTRACT,
    RetrievalSecurityContract,
    filter_authorized_chunks,
)

_TOKEN_PATTERN = re.compile(r"[a-z0-9:.\-]+", re.IGNORECASE)


def _tokenize(value: str) -> list[str]:
    return [token.lower() for token in _TOKEN_PATTERN.findall(value)]


def _character_ngrams(token: str, size: int = 3) -> list[str]:
    normalized = token.replace(" ", "")
    if len(normalized) < size:
        return [normalized]
    return [normalized[index : index + size] for index in range(len(normalized) - size + 1)]


def _hashed_index(token: str, dimensions: int) -> int:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).hexdigest()
    return int(digest, 16) % dimensions


def embed_text(value: str, *, dimensions: int = 256) -> dict[int, float]:
    weights: dict[int, float] = {}
    for token in _tokenize(value):
        token_index = _hashed_index(f"tok:{token}", dimensions)
        weights[token_index] = weights.get(token_index, 0.0) + 1.0
        for gram in _character_ngrams(token):
            gram_index = _hashed_index(f"tri:{gram}", dimensions)
            weights[gram_index] = weights.get(gram_index, 0.0) + 0.35

    norm = math.sqrt(sum(weight * weight for weight in weights.values()))
    if norm == 0.0:
        return {}
    return {index: weight / norm for index, weight in weights.items()}


def _cosine_similarity(left: dict[int, float], right: dict[int, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(index, 0.0) for index, value in left.items())


def _dense_text(chunk: ChunkRecord) -> str:
    return " ".join(
        part
        for part in (
            chunk.citation_path,
            chunk.text,
            chunk.article or "",
            chunk.ecli or "",
            chunk.section_type or "",
        )
        if part
    )


def _rank_dense_chunks(
    chunks: list[ChunkRecord] | tuple[ChunkRecord, ...],
    request: RetrievalRequest,
) -> tuple[RetrievalResult, ...]:
    dimensions = 256
    query_embedding = embed_text(request.query, dimensions=dimensions)
    scored_candidates: list[tuple[float, ChunkRecord]] = []

    for chunk in chunks:
        chunk_embedding = embed_text(_dense_text(chunk), dimensions=dimensions)
        similarity = _cosine_similarity(query_embedding, chunk_embedding)
        if similarity <= 0.0:
            continue
        scored_candidates.append((similarity, chunk))

    scored_candidates.sort(key=lambda item: (-item[0], item[1].chunk_id))
    top_candidates = scored_candidates[: request.top_k]

    results: list[RetrievalResult] = []
    for rank, (similarity, chunk) in enumerate(top_candidates, start=1):
        results.append(
            RetrievalResult.from_chunk(
                chunk,
                retrieval_method=RetrievalMethod.DENSE,
                scores=(
                    ScoreTrace(metric="dense_cosine_similarity", value=similarity, rank=rank),
                    ScoreTrace(metric="dense_score", value=similarity, rank=rank, metadata={"dimensions": dimensions}),
                ),
                metadata={"rank": rank, "authorized": True},
            )
        )
    return tuple(results)


def retrieve_dense(
    chunks: list[ChunkRecord] | tuple[ChunkRecord, ...],
    request: RetrievalRequest,
    *,
    contract: RetrievalSecurityContract = DEFAULT_RETRIEVAL_SECURITY_CONTRACT,
) -> RetrievalResponse:
    authorized = filter_authorized_chunks(chunks, role=request.role, contract=contract)
    request_scoped_chunks = [chunk for chunk in authorized.authorized_chunks if request_allows_chunk(chunk, request)]
    results = _rank_dense_chunks(request_scoped_chunks, request)

    return RetrievalResponse(
        request=request,
        retrieval_method=RetrievalMethod.DENSE,
        results=results,
        security_stage=authorized.enforcement_stage,
        metadata={
            "authorized_candidate_count": len(request_scoped_chunks),
            "denied_count": authorized.denied_count,
            "total_chunk_count": len(chunks),
            "dense_model": "demo-hash-embedding-v1",
            "dense_dimensions": 256,
        },
    )
