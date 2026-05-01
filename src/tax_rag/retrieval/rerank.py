"""Configurable reranking for inspectable legal retrieval outputs."""

from __future__ import annotations

import re
from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol, cast

from tax_rag.common import DEFAULT_CONFIG
from tax_rag.retrieval.semantic import semantic_term_set
from tax_rag.schemas import RetrievalResult, RetrievalRequest, ScoreTrace, SourceType

_EXACT_IDENTIFIER_PATTERN = re.compile(r"\b(?:ecli:|artikel|article|art\.)", re.IGNORECASE)


class RerankerBackend(Protocol):
    name: str
    model_name: str

    def rerank(
        self, results: tuple[RetrievalResult, ...], request: RetrievalRequest
    ) -> tuple[RetrievalResult, ...]: ...


class CrossEncoderModel(Protocol):
    def predict(self, pairs: Sequence[tuple[str, str]]) -> Sequence[float]: ...


class RerankerUnavailableError(RuntimeError):
    """Raised when a configured reranker backend cannot run in the local environment."""


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _generic_rule_bonus(result: RetrievalResult, query_terms: frozenset[str], query: str) -> float:
    if _EXACT_IDENTIFIER_PATTERN.search(query):
        return 0.0
    if result.source.source_type is not SourceType.LEGISLATION:
        return 0.0

    bonus = 0.0
    if "concept:thirty_percent_ruling" in query_terms:
        bonus += DEFAULT_CONFIG.reranking.legislation_bonus
    if "concept:employment_change" in query_terms and "concept:employer" in query_terms:
        bonus += DEFAULT_CONFIG.reranking.legislation_bonus
    return min(bonus, DEFAULT_CONFIG.reranking.max_source_bonus)


class DeterministicReranker:
    name = "deterministic"
    model_name = DEFAULT_CONFIG.reranking.model

    def rerank(self, results: tuple[RetrievalResult, ...], request: RetrievalRequest) -> tuple[RetrievalResult, ...]:
        if not results:
            return ()

        query_terms = semantic_term_set(request.query)
        query_concepts = {term for term in query_terms if term.startswith("concept:")}
        query_lexical_terms = query_terms - query_concepts

        scored_results: list[tuple[float, RetrievalResult, tuple[ScoreTrace, ...]]] = []
        for result in results:
            result_text = " ".join(
                part
                for part in (
                    result.source.citation_path,
                    result.text,
                    result.source.source_type.value,
                    result.source.section_type or "",
                )
                if part
            )
            result_terms = semantic_term_set(result_text)
            result_concepts = {term for term in result_terms if term.startswith("concept:")}
            result_lexical_terms = result_terms - result_concepts

            concept_overlap = _ratio(len(query_concepts & result_concepts), len(query_concepts))
            lexical_overlap = _ratio(len(query_lexical_terms & result_lexical_terms), len(query_lexical_terms))
            dense_signal = result.score_map().get("dense_score", result.score_map().get("qdrant_score", 0.0))
            lexical_signal = min(
                result.score_map().get("lexical_score", 0.0) / DEFAULT_CONFIG.reranking.lexical_normalizer,
                1.0,
            )
            rrf_signal = min(
                result.score_map().get("rrf_score", 0.0) / DEFAULT_CONFIG.reranking.rrf_normalizer,
                1.0,
            )
            source_bonus = _generic_rule_bonus(result, query_terms, request.query)

            rerank_score = (
                DEFAULT_CONFIG.reranking.concept_overlap_weight * concept_overlap
                + DEFAULT_CONFIG.reranking.lexical_overlap_weight * lexical_overlap
                + DEFAULT_CONFIG.reranking.dense_weight * dense_signal
                + DEFAULT_CONFIG.reranking.lexical_weight * lexical_signal
                + DEFAULT_CONFIG.reranking.rrf_weight * rrf_signal
                + source_bonus
            )
            rerank_scores = (
                ScoreTrace(
                    metric="rerank_backend", value=1.0, metadata={"backend": self.name, "model": self.model_name}
                ),
                ScoreTrace(metric="rerank_concept_overlap", value=concept_overlap),
                ScoreTrace(metric="rerank_lexical_overlap", value=lexical_overlap),
                ScoreTrace(metric="rerank_dense_signal", value=dense_signal),
                ScoreTrace(metric="rerank_source_bonus", value=source_bonus),
                ScoreTrace(metric="rerank_score", value=rerank_score),
            )
            scored_results.append((rerank_score, result, rerank_scores))

        scored_results.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return _with_rerank_scores(scored_results)


class CrossEncoderReranker:
    name = "cross_encoder"

    def __init__(
        self,
        model_name: str = DEFAULT_CONFIG.reranking.cross_encoder_model,
        model: CrossEncoderModel | None = None,
    ) -> None:
        self.model_name = model_name
        self._model = model

    def _load_model(self) -> CrossEncoderModel:
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RerankerUnavailableError(
                "Cross-encoder reranking requires the optional 'sentence-transformers' package."
            ) from exc
        self._model = cast(CrossEncoderModel, CrossEncoder(self.model_name))
        return self._model

    def rerank(self, results: tuple[RetrievalResult, ...], request: RetrievalRequest) -> tuple[RetrievalResult, ...]:
        if not results:
            return ()

        model = self._load_model()
        pairs = [(request.query, f"{result.source.citation_path}\n{result.text}") for result in results]
        raw_scores = model.predict(pairs)

        scored_results: list[tuple[float, RetrievalResult, tuple[ScoreTrace, ...]]] = []
        for score, result in zip(raw_scores, results, strict=True):
            rerank_score = float(score)
            scored_results.append(
                (
                    rerank_score,
                    result,
                    (
                        ScoreTrace(
                            metric="rerank_backend",
                            value=1.0,
                            metadata={"backend": self.name, "model": self.model_name},
                        ),
                        ScoreTrace(metric="rerank_score", value=rerank_score),
                    ),
                )
            )
        scored_results.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return _with_rerank_scores(scored_results)


def _with_rerank_scores(
    scored_results: list[tuple[float, RetrievalResult, tuple[ScoreTrace, ...]]],
) -> tuple[RetrievalResult, ...]:
    reranked: list[RetrievalResult] = []
    for rank, (_, result, rerank_scores) in enumerate(scored_results, start=1):
        updated_scores = [
            ScoreTrace(metric=score.metric, value=score.value, rank=score.rank, metadata=score.metadata)
            for score in result.scores
        ]
        updated_scores.extend(
            ScoreTrace(metric=score.metric, value=score.value, rank=rank, metadata=score.metadata)
            for score in rerank_scores
        )
        reranked.append(
            RetrievalResult(
                source=result.source,
                text=result.text,
                retrieval_method=result.retrieval_method,
                scores=tuple(updated_scores),
                matched_terms=result.matched_terms,
                metadata={**result.metadata, "rank": rank, "reranked": True},
            )
        )
    return tuple(reranked)


@lru_cache(maxsize=1)
def _cross_encoder_backend() -> CrossEncoderReranker:
    return CrossEncoderReranker()


def get_reranker_backend(name: str | None = None) -> RerankerBackend:
    backend_name = (name or DEFAULT_CONFIG.reranking.backend).strip().lower()
    if backend_name == "deterministic":
        return DeterministicReranker()
    if backend_name in {"cross_encoder", "cross-encoder"}:
        return _cross_encoder_backend()
    raise ValueError(f"Unsupported reranker backend: {backend_name}")


def rerank_results(
    results: tuple[RetrievalResult, ...],
    request: RetrievalRequest,
    *,
    backend: RerankerBackend | None = None,
) -> tuple[RetrievalResult, ...]:
    return (backend or get_reranker_backend()).rerank(results, request)
