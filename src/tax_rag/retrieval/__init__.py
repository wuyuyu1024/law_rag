"""Retrieval module for tax_rag."""

from tax_rag.retrieval.lexical import load_chunk_records, retrieve_lexical
from tax_rag.schemas.retrieval import (
    RetrievalMethod,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    ScoreTrace,
    SourceReference,
)

__all__ = [
    "load_chunk_records",
    "retrieve_lexical",
    "RetrievalMethod",
    "RetrievalRequest",
    "RetrievalResponse",
    "RetrievalResult",
    "ScoreTrace",
    "SourceReference",
]
