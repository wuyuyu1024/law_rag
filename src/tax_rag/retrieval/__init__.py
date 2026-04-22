"""Retrieval module for tax_rag."""

from tax_rag.retrieval.common import load_chunk_records
from tax_rag.retrieval.dense import embed_text, retrieve_dense
from tax_rag.retrieval.hybrid import retrieve_hybrid
from tax_rag.retrieval.lexical import retrieve_lexical
from tax_rag.schemas.retrieval import (
    RetrievalMethod,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    ScoreTrace,
    SourceReference,
)

__all__ = [
    "embed_text",
    "load_chunk_records",
    "retrieve_dense",
    "retrieve_hybrid",
    "retrieve_lexical",
    "RetrievalMethod",
    "RetrievalRequest",
    "RetrievalResponse",
    "RetrievalResult",
    "ScoreTrace",
    "SourceReference",
]
