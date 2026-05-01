"""Retrieval module for tax_rag."""

from tax_rag.retrieval.citations import ResolvedCitation, resolve_result_citation, resolve_source_reference
from tax_rag.retrieval.common import load_chunk_records
from tax_rag.retrieval.dense import embed_text, retrieve_dense
from tax_rag.retrieval.hybrid import retrieve_hybrid
from tax_rag.retrieval.lexical import retrieve_lexical
from tax_rag.retrieval.rerank import (
    CrossEncoderReranker,
    DeterministicReranker,
    RerankerBackend,
    RerankerUnavailableError,
    get_reranker_backend,
    rerank_results,
)
from tax_rag.retrieval.service import RetrievalService
from tax_rag.schemas.retrieval import (
    RetrievalMethod,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    ScoreTrace,
    SourceReference,
)

__all__ = [
    "ResolvedCitation",
    "RetrievalService",
    "CrossEncoderReranker",
    "DeterministicReranker",
    "RerankerBackend",
    "RerankerUnavailableError",
    "embed_text",
    "get_reranker_backend",
    "load_chunk_records",
    "retrieve_dense",
    "retrieve_hybrid",
    "retrieve_lexical",
    "rerank_results",
    "resolve_result_citation",
    "resolve_source_reference",
    "RetrievalMethod",
    "RetrievalRequest",
    "RetrievalResponse",
    "RetrievalResult",
    "ScoreTrace",
    "SourceReference",
]
