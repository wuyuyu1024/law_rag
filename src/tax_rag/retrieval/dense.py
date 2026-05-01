"""Qdrant-backed dense retrieval over RBAC-authorized chunk candidates."""

from __future__ import annotations

from datetime import datetime
from time import perf_counter

from qdrant_client import QdrantClient, models

from tax_rag.common import DEFAULT_CONFIG
from tax_rag.common.dense import CLASSIFICATION_ORDER, dense_text, embed_text, payload_for_chunk
from tax_rag.indexing import DEFAULT_DENSE_COLLECTION_NAME, ensure_local_qdrant_index, qdrant_vector_params
from tax_rag.retrieval.common import scope_chunks_for_request
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
    DEFAULT_ROLE_CLASSIFICATION_CLEARANCE,
    RetrievalSecurityContract,
    filter_authorized_chunks,
)

def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 3)


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
            range=models.Range(lte=CLASSIFICATION_ORDER[clearance]),
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

    if request.as_of_date is not None:
        as_of = datetime.fromisoformat(request.as_of_date)
        must.append(
            models.Filter(
                should=[
                    models.IsEmptyCondition(is_empty=models.PayloadField(key="valid_from")),
                    models.FieldCondition(key="valid_from", range=models.DatetimeRange(lte=as_of)),
                ]
            )
        )
        must.append(
            models.Filter(
                should=[
                    models.IsEmptyCondition(is_empty=models.PayloadField(key="valid_to")),
                    models.FieldCondition(key="valid_to", range=models.DatetimeRange(gte=as_of)),
                ]
            )
        )

    return models.Filter(must=must)


def _build_local_qdrant(chunks: list[ChunkRecord] | tuple[ChunkRecord, ...], *, dimensions: int) -> QdrantClient:
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name="dense_chunks",
        vectors_config=qdrant_vector_params(dimensions),
    )
    client.upload_collection(
        collection_name="dense_chunks",
        ids=list(range(1, len(chunks) + 1)),
        vectors=[embed_text(dense_text(chunk), dimensions=dimensions) for chunk in chunks],
        payload=[payload_for_chunk(chunk) for chunk in chunks],
    )
    return client


def _persistent_index_settings(request: RetrievalRequest) -> tuple[str | None, str]:
    path = request.metadata.get("dense_index_path")
    collection_name = request.metadata.get("dense_collection_name", DEFAULT_DENSE_COLLECTION_NAME)
    if not isinstance(path, str) or not path.strip():
        return None, collection_name
    if not isinstance(collection_name, str) or not collection_name.strip():
        collection_name = DEFAULT_DENSE_COLLECTION_NAME
    return path, collection_name


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

    persistent_index_path, collection_name = _persistent_index_settings(request)
    backend = "qdrant_local"
    if persistent_index_path is not None:
        ensure_local_qdrant_index(
            chunks,
            path=persistent_index_path,
            collection_name=collection_name,
            dimensions=dimensions,
        )
        client = QdrantClient(path=persistent_index_path)
        backend = "qdrant_local_persistent"
    else:
        client = _build_local_qdrant(chunks, dimensions=dimensions)
        collection_name = DEFAULT_DENSE_COLLECTION_NAME
    search_result = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=query_filter,
        search_params=models.SearchParams(hnsw_ef=DEFAULT_CONFIG.retrieval.qdrant_search_ef),
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
                            "backend": backend,
                            "dimensions": dimensions,
                        },
                    ),
                ),
                metadata={"rank": rank, "authorized": True, "backend": backend},
            )
        )
    return tuple(results)


def retrieve_dense(
    chunks: list[ChunkRecord] | tuple[ChunkRecord, ...],
    request: RetrievalRequest,
    *,
    contract: RetrievalSecurityContract = DEFAULT_RETRIEVAL_SECURITY_CONTRACT,
) -> RetrievalResponse:
    total_start = perf_counter()
    filter_start = perf_counter()
    authorized = filter_authorized_chunks(chunks, role=request.role, contract=contract)
    request_scope = scope_chunks_for_request(authorized.authorized_chunks, request)
    security_filter_ms = _elapsed_ms(filter_start)
    dense_start = perf_counter()
    results = _rank_dense_chunks(request_scope.chunks, request)
    dense_retrieval_ms = _elapsed_ms(dense_start)
    retrieval_total_ms = _elapsed_ms(total_start)

    return RetrievalResponse(
        request=request,
        retrieval_method=RetrievalMethod.DENSE,
        results=results,
        security_stage=authorized.enforcement_stage,
        metadata={
            "authorized_candidate_count": len(request_scope.chunks),
            "denied_count": authorized.denied_count,
            "total_chunk_count": len(chunks),
            "source_type_filtered_count": request_scope.source_type_filtered_count,
            "jurisdiction_filtered_count": request_scope.jurisdiction_filtered_count,
            "validity_filtered_count": request_scope.validity_filtered_count,
            "as_of_date": request.as_of_date,
            "dense_model": DEFAULT_CONFIG.retrieval.dense_model,
            "dense_dimensions": DEFAULT_CONFIG.retrieval.dense_dimensions,
            "vector_backend": (
                "qdrant_local_persistent" if _persistent_index_settings(request)[0] is not None else "qdrant_local"
            ),
            "dense_collection_name": _persistent_index_settings(request)[1],
            "timings_ms": {
                "request_scoping_ms": 0.0,
                "security_filter_ms": security_filter_ms,
                "lexical_retrieval_ms": 0.0,
                "dense_retrieval_ms": dense_retrieval_ms,
                "fusion_ms": 0.0,
                "reranking_ms": 0.0,
                "retrieval_total_ms": retrieval_total_ms,
            },
        },
    )
