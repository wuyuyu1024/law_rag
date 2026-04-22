"""Hybrid retrieval with pre-retrieval RBAC filtering and RRF fusion."""

from __future__ import annotations

import re

from tax_rag.common import DEFAULT_CONFIG
from tax_rag.retrieval.common import request_allows_chunk
from tax_rag.retrieval.dense import _rank_dense_chunks
from tax_rag.retrieval.lexical import _rank_lexical_chunks
from tax_rag.retrieval.rerank import rerank_results
from tax_rag.schemas import RetrievalMethod, RetrievalRequest, RetrievalResponse, RetrievalResult, ScoreTrace
from tax_rag.security import (
    DEFAULT_RETRIEVAL_SECURITY_CONTRACT,
    RetrievalSecurityContract,
    filter_authorized_chunks,
)

_EXACT_IDENTIFIER_PATTERN = re.compile(r"\b(?:ecli:|artikel|article|art\.?)", re.IGNORECASE)


def _rrf_contribution(rank: int, *, rrf_k: int) -> float:
    return 1.0 / (rrf_k + rank)


def _exact_priority(scores: list[ScoreTrace]) -> float:
    exact_metrics = {
        "ecli_exact_match",
        "article_exact_match",
        "paragraph_exact_match",
        "subparagraph_exact_match",
        "citation_path_exact_match",
    }
    return sum(score.value for score in scores if score.metric in exact_metrics)


def retrieve_hybrid(
    chunks,
    request: RetrievalRequest,
    *,
    contract: RetrievalSecurityContract = DEFAULT_RETRIEVAL_SECURITY_CONTRACT,
) -> RetrievalResponse:
    authorized = filter_authorized_chunks(chunks, role=request.role, contract=contract)
    authorized_chunks = [chunk for chunk in authorized.authorized_chunks if request_allows_chunk(chunk, request)]

    lexical_request = RetrievalRequest(
        query=request.query,
        role=request.role,
        top_k=max(request.top_k, DEFAULT_CONFIG.retrieval.lexical_top_k),
        source_types=request.source_types,
        jurisdiction=request.jurisdiction,
        metadata=request.metadata,
    )
    dense_request = RetrievalRequest(
        query=request.query,
        role=request.role,
        top_k=max(request.top_k, DEFAULT_CONFIG.retrieval.dense_top_k),
        source_types=request.source_types,
        jurisdiction=request.jurisdiction,
        metadata=request.metadata,
    )

    lexical_results = _rank_lexical_chunks(authorized_chunks, lexical_request)
    dense_results = _rank_dense_chunks(authorized_chunks, dense_request)
    rrf_k = DEFAULT_CONFIG.retrieval.rrf_k

    by_chunk_id: dict[str, dict[str, object]] = {}

    for result in lexical_results:
        entry = by_chunk_id.setdefault(
            result.chunk_id,
            {
                "result": result,
                "matched_terms": set(result.matched_terms),
                "scores": list(result.scores),
                "rrf_score": 0.0,
            },
        )
        rank = result.metadata["rank"]
        contribution = _rrf_contribution(rank, rrf_k=rrf_k)
        entry["rrf_score"] = entry["rrf_score"] + contribution
        entry["scores"].append(
            ScoreTrace(metric="rrf_lexical", value=contribution, rank=rank, metadata={"source_rank": rank})
        )

    for result in dense_results:
        entry = by_chunk_id.setdefault(
            result.chunk_id,
            {
                "result": result,
                "matched_terms": set(result.matched_terms),
                "scores": list(result.scores),
                "rrf_score": 0.0,
            },
        )
        if entry["result"].retrieval_method is RetrievalMethod.DENSE:
            entry["result"] = result
        entry["matched_terms"].update(result.matched_terms)
        existing_metrics = {score.metric for score in entry["scores"]}
        for score in result.scores:
            if score.metric not in existing_metrics:
                entry["scores"].append(score)
        rank = result.metadata["rank"]
        contribution = _rrf_contribution(rank, rrf_k=rrf_k)
        entry["rrf_score"] = entry["rrf_score"] + contribution
        entry["scores"].append(
            ScoreTrace(metric="rrf_dense", value=contribution, rank=rank, metadata={"source_rank": rank})
        )

    fused_candidates: list[tuple[float, float, RetrievalResult, set[str], list[ScoreTrace]]] = []
    for entry in by_chunk_id.values():
        base_result = entry["result"]
        scores = list(entry["scores"])
        scores.append(ScoreTrace(metric="rrf_score", value=entry["rrf_score"]))
        fused_candidates.append((_exact_priority(scores), entry["rrf_score"], base_result, entry["matched_terms"], scores))

    if _EXACT_IDENTIFIER_PATTERN.search(request.query):
        fused_candidates.sort(key=lambda item: (-item[0], -item[1], item[2].chunk_id))
    else:
        fused_candidates.sort(key=lambda item: (-item[1], item[2].chunk_id))
    candidate_limit = max(request.top_k, DEFAULT_CONFIG.reranking.input_top_k)
    top_candidates = fused_candidates[:candidate_limit]

    results: list[RetrievalResult] = []
    for rank, (_, _, base_result, matched_terms, scores) in enumerate(top_candidates, start=1):
        ranked_scores = tuple(
            ScoreTrace(metric=score.metric, value=score.value, rank=rank if score.rank is None else score.rank, metadata=score.metadata)
            for score in scores
        )
        results.append(
            RetrievalResult(
                source=base_result.source,
                text=base_result.text,
                retrieval_method=RetrievalMethod.HYBRID,
                scores=ranked_scores,
                matched_terms=tuple(sorted(matched_terms)),
                metadata={"rank": rank, "authorized": True},
            )
        )

    reranking_applied = False
    should_rerank = DEFAULT_CONFIG.reranking.enabled and _EXACT_IDENTIFIER_PATTERN.search(request.query) is None
    if should_rerank:
        reranking_applied = True
        results = list(rerank_results(tuple(results), request))

    results = results[: request.top_k]

    return RetrievalResponse(
        request=request,
        retrieval_method=RetrievalMethod.HYBRID,
        results=tuple(results),
        security_stage=authorized.enforcement_stage,
        metadata={
            "authorized_candidate_count": len(authorized_chunks),
            "denied_count": authorized.denied_count,
            "total_chunk_count": len(chunks),
            "lexical_result_count": len(lexical_results),
            "dense_result_count": len(dense_results),
            "fusion_strategy": DEFAULT_CONFIG.retrieval.fusion_strategy,
            "rrf_k": rrf_k,
            "reranking_enabled": DEFAULT_CONFIG.reranking.enabled,
            "reranking_applied": reranking_applied,
            "reranker_model": DEFAULT_CONFIG.reranking.model if reranking_applied else None,
            "reranker_input_count": len(top_candidates) if reranking_applied else 0,
        },
    )
