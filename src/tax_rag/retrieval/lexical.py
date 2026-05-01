"""Exact-match lexical retrieval over RBAC-authorized chunk candidates."""

from __future__ import annotations

import re
from time import perf_counter

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

_ECLI_PATTERN = re.compile(r"\bECLI:[A-Z]{2}:[A-Z0-9]+:\d{4}:[A-Z0-9]+\b", re.IGNORECASE)
_ARTICLE_PATTERN = re.compile(r"\b(?:artikel|article|art\.?)\s+([0-9]+[a-z]*(?:[.:][0-9]+[a-z]*)*)\b", re.IGNORECASE)
_PARAGRAPH_PATTERN = re.compile(r"\b(?:lid|paragraph)\s+([0-9]+)\b", re.IGNORECASE)
_SUBPARAGRAPH_PATTERN = re.compile(r"\b(?:onderdeel|subparagraph|sub)\s+([a-z])\b", re.IGNORECASE)
_NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 3)


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _normalize_for_match(value: str | None) -> str:
    if not value:
        return ""
    return _NON_ALNUM_PATTERN.sub(" ", value.lower()).strip()


def _normalize_subparagraph(value: str | None) -> str:
    return _normalize_for_match(value).replace(" ", "")


def _extract_query_terms(query: str) -> dict[str, str]:
    ecli_match = _ECLI_PATTERN.search(query)
    article_match = _ARTICLE_PATTERN.search(query)
    paragraph_match = _PARAGRAPH_PATTERN.search(query)
    subparagraph_match = _SUBPARAGRAPH_PATTERN.search(query)

    terms: dict[str, str] = {}
    if ecli_match is not None:
        terms["ecli"] = ecli_match.group(0).upper()
    if article_match is not None:
        terms["article"] = article_match.group(1)
    if paragraph_match is not None:
        terms["paragraph"] = paragraph_match.group(1)
    if subparagraph_match is not None:
        terms["subparagraph"] = subparagraph_match.group(1).lower()
    return terms


def _score_chunk_against_query(chunk: ChunkRecord, query: str) -> tuple[tuple[ScoreTrace, ...], tuple[str, ...]]:
    query_terms = _extract_query_terms(query)
    scores: list[ScoreTrace] = []
    matched_terms: list[str] = []
    exact_identifier_boost = DEFAULT_CONFIG.retrieval.exact_identifier_boost

    if query_terms.get("ecli") and chunk.ecli and query_terms["ecli"] == chunk.ecli.upper():
        scores.append(
            ScoreTrace(
                metric="ecli_exact_match",
                value=100.0 * exact_identifier_boost,
                metadata={"field": "ecli"},
            )
        )
        matched_terms.append(query_terms["ecli"])

    if query_terms.get("article") and chunk.article and query_terms["article"] == chunk.article:
        article_score = 40.0 * exact_identifier_boost
        scores.append(
            ScoreTrace(
                metric="article_exact_match",
                value=article_score,
                metadata={"field": "article"},
            )
        )
        matched_terms.append(f"article:{query_terms['article']}")

        if query_terms.get("paragraph") and chunk.paragraph == query_terms["paragraph"]:
            scores.append(
                ScoreTrace(
                    metric="paragraph_exact_match",
                    value=20.0,
                    metadata={"field": "paragraph"},
                )
            )
            matched_terms.append(f"paragraph:{query_terms['paragraph']}")

        if query_terms.get("subparagraph") and _normalize_subparagraph(chunk.subparagraph) == query_terms["subparagraph"]:
            scores.append(
                ScoreTrace(
                    metric="subparagraph_exact_match",
                    value=10.0,
                    metadata={"field": "subparagraph"},
                )
            )
            matched_terms.append(f"subparagraph:{query_terms['subparagraph']}")

    normalized_query = _normalize_for_match(query)
    normalized_citation_path = _normalize_for_match(chunk.citation_path)
    if normalized_query and normalized_query == normalized_citation_path:
        scores.append(
            ScoreTrace(
                metric="citation_path_exact_match",
                value=95.0,
                metadata={"field": "citation_path"},
            )
        )
        matched_terms.append(f"citation:{normalized_query}")
    elif normalized_query and normalized_query in normalized_citation_path:
        scores.append(
            ScoreTrace(
                metric="citation_path_contains_match",
                value=55.0,
                metadata={"field": "citation_path"},
            )
        )
        matched_terms.append(f"citation:{normalized_query}")

    if not scores:
        return (), ()

    lexical_score = sum(score.value for score in scores)
    scores.append(ScoreTrace(metric="lexical_score", value=lexical_score))
    return tuple(scores), tuple(dict.fromkeys(matched_terms))


def _rank_lexical_chunks(
    chunks: list[ChunkRecord] | tuple[ChunkRecord, ...],
    request: RetrievalRequest,
) -> tuple[RetrievalResult, ...]:
    scored_candidates: list[tuple[float, ChunkRecord, tuple[ScoreTrace, ...], tuple[str, ...]]] = []
    for chunk in chunks:
        score_traces, matched_terms = _score_chunk_against_query(chunk, request.query)
        if not score_traces:
            continue
        lexical_score = next(score.value for score in score_traces if score.metric == "lexical_score")
        scored_candidates.append((lexical_score, chunk, score_traces, matched_terms))

    scored_candidates.sort(key=lambda item: (-item[0], item[1].chunk_id))
    top_candidates = scored_candidates[: request.top_k]

    results: list[RetrievalResult] = []
    for rank, (_, chunk, score_traces, matched_terms) in enumerate(top_candidates, start=1):
        ranked_scores = tuple(
            ScoreTrace(
                metric=score.metric,
                value=score.value,
                rank=rank,
                metadata=score.metadata,
            )
            for score in score_traces
        )
        results.append(
            RetrievalResult.from_chunk(
                chunk,
                retrieval_method=RetrievalMethod.LEXICAL,
                scores=ranked_scores,
                matched_terms=matched_terms,
                metadata={"rank": rank, "authorized": True},
            )
        )
    return tuple(results)


def retrieve_lexical(
    chunks: list[ChunkRecord] | tuple[ChunkRecord, ...],
    request: RetrievalRequest,
    *,
    contract: RetrievalSecurityContract = DEFAULT_RETRIEVAL_SECURITY_CONTRACT,
) -> RetrievalResponse:
    total_start = perf_counter()
    filter_start = perf_counter()
    authorized = filter_authorized_chunks(chunks, role=request.role, contract=contract)
    request_scoped_chunks = [chunk for chunk in authorized.authorized_chunks if request_allows_chunk(chunk, request)]
    security_filter_ms = _elapsed_ms(filter_start)
    lexical_start = perf_counter()
    results = _rank_lexical_chunks(request_scoped_chunks, request)
    lexical_retrieval_ms = _elapsed_ms(lexical_start)
    retrieval_total_ms = _elapsed_ms(total_start)

    return RetrievalResponse(
        request=request,
        retrieval_method=RetrievalMethod.LEXICAL,
        results=results,
        security_stage=authorized.enforcement_stage,
        metadata={
            "authorized_candidate_count": len(request_scoped_chunks),
            "denied_count": authorized.denied_count,
            "total_chunk_count": len(chunks),
            "query_terms": _extract_query_terms(request.query),
            "timings_ms": {
                "request_scoping_ms": 0.0,
                "security_filter_ms": security_filter_ms,
                "lexical_retrieval_ms": lexical_retrieval_ms,
                "dense_retrieval_ms": 0.0,
                "fusion_ms": 0.0,
                "reranking_ms": 0.0,
                "retrieval_total_ms": retrieval_total_ms,
            },
        },
    )
