"""Qdrant-backed dense retrieval over RBAC-authorized chunk candidates."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any

from qdrant_client import QdrantClient, models

from tax_rag.common import DEFAULT_CONFIG
from tax_rag.schemas import (
    ChunkRecord,
    RetrievalMethod,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    ScoreTrace,
    SecurityClassification,
)
from tax_rag.security import (
    DEFAULT_RETRIEVAL_SECURITY_CONTRACT,
    DEFAULT_ROLE_CLASSIFICATION_CLEARANCE,
    RetrievalSecurityContract,
    filter_authorized_chunks,
)

_TOKEN_PATTERN = re.compile(r"[a-z0-9:.\-]+", re.IGNORECASE)
_CLASSIFICATION_ORDER = {
    SecurityClassification.PUBLIC: 0,
    SecurityClassification.INTERNAL: 1,
    SecurityClassification.CONFIDENTIAL: 2,
    SecurityClassification.RESTRICTED: 3,
}


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


def embed_text(value: str, *, dimensions: int = 256) -> list[float]:
    weights = [0.0] * dimensions
    for token in _tokenize(value):
        token_index = _hashed_index(f"tok:{token}", dimensions)
        weights[token_index] += 1.0
        for gram in _character_ngrams(token):
            gram_index = _hashed_index(f"tri:{gram}", dimensions)
            weights[gram_index] += 0.35

    norm = math.sqrt(sum(weight * weight for weight in weights))
    if norm == 0.0:
        return weights
    return [weight / norm for weight in weights]


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


def _payload_for_chunk(chunk: ChunkRecord) -> dict[str, Any]:
    return {
        "chunk": chunk.to_dict(),
        "allowed_roles": list(chunk.allowed_roles),
        "source_type": chunk.source_type.value,
        "jurisdiction": chunk.jurisdiction,
        "security_classification": chunk.security_classification.value,
        "security_classification_rank": _CLASSIFICATION_ORDER[chunk.security_classification],
    }


def _query_filter(request: RetrievalRequest) -> models.Filter | None:
    clearance = DEFAULT_ROLE_CLASSIFICATION_CLEARANCE.get(request.role)
    if clearance is None:
        return None

    must: list[models.Condition] = [
        models.FieldCondition(
            key="allowed_roles",
            match=models.MatchAny(any=[request.role]),
        ),
        models.FieldCondition(
            key="security_classification_rank",
            range=models.Range(lte=_CLASSIFICATION_ORDER[clearance]),
        ),
    ]

    if request.source_types:
        must.append(
            models.FieldCondition(
                key="source_type",
                match=models.MatchAny(any=[source_type.value for source_type in request.source_types]),
            )
        )

    if request.jurisdiction is not None:
        must.append(
            models.FieldCondition(
                key="jurisdiction",
                match=models.MatchValue(value=request.jurisdiction),
            )
        )

    return models.Filter(must=must)


def _build_local_qdrant(chunks: list[ChunkRecord] | tuple[ChunkRecord, ...], *, dimensions: int) -> QdrantClient:
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name="dense_chunks",
        vectors_config=models.VectorParams(size=dimensions, distance=models.Distance.COSINE),
    )
    client.upload_collection(
        collection_name="dense_chunks",
        ids=list(range(1, len(chunks) + 1)),
        vectors=[embed_text(_dense_text(chunk), dimensions=dimensions) for chunk in chunks],
        payload=[_payload_for_chunk(chunk) for chunk in chunks],
    )
    return client


def _rank_dense_chunks(
    chunks: list[ChunkRecord] | tuple[ChunkRecord, ...],
    request: RetrievalRequest,
) -> tuple[RetrievalResult, ...]:
    if not chunks:
        return ()

    dimensions = DEFAULT_CONFIG.retrieval.dense_dimensions
    query_vector = embed_text(request.query, dimensions=dimensions)
    if not any(query_vector):
        return ()

    query_filter = _query_filter(request)
    if query_filter is None:
        return ()

    client = _build_local_qdrant(chunks, dimensions=dimensions)
    search_result = client.query_points(
        collection_name="dense_chunks",
        query=query_vector,
        query_filter=query_filter,
        limit=request.top_k,
        with_payload=True,
    )

    results: list[RetrievalResult] = []
    for rank, point in enumerate(search_result.points, start=1):
        payload = point.payload or {}
        chunk_payload = payload.get("chunk")
        if not isinstance(chunk_payload, dict):
            continue
        chunk = ChunkRecord.from_dict(chunk_payload)
        similarity = float(point.score)
        results.append(
            RetrievalResult.from_chunk(
                chunk,
                retrieval_method=RetrievalMethod.DENSE,
                scores=(
                    ScoreTrace(metric="qdrant_score", value=similarity, rank=rank),
                    ScoreTrace(
                        metric="dense_score",
                        value=similarity,
                        rank=rank,
                        metadata={
                            "backend": "qdrant_local",
                            "dimensions": dimensions,
                        },
                    ),
                ),
                metadata={"rank": rank, "authorized": True, "backend": "qdrant_local"},
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
    request_scoped_chunks = tuple(
        chunk
        for chunk in authorized.authorized_chunks
        if (not request.source_types or chunk.source_type in request.source_types)
        and (request.jurisdiction is None or chunk.jurisdiction == request.jurisdiction)
    )
    results = _rank_dense_chunks(chunks, request)

    return RetrievalResponse(
        request=request,
        retrieval_method=RetrievalMethod.DENSE,
        results=results,
        security_stage=authorized.enforcement_stage,
        metadata={
            "authorized_candidate_count": len(request_scoped_chunks),
            "denied_count": authorized.denied_count,
            "total_chunk_count": len(chunks),
            "dense_model": DEFAULT_CONFIG.retrieval.dense_model,
            "dense_dimensions": DEFAULT_CONFIG.retrieval.dense_dimensions,
            "vector_backend": "qdrant_local",
        },
    )
