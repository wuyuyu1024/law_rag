"""Typed contracts shared across modules."""

from tax_rag.schemas.chunk import ChunkRecord
from tax_rag.schemas.document import (
    NormalizedDocument,
    SecurityClassification,
    SourceType,
)
from tax_rag.schemas.retrieval import (
    RetrievalMethod,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    ScoreTrace,
    SourceReference,
)

__all__ = [
    "ChunkRecord",
    "NormalizedDocument",
    "RetrievalMethod",
    "RetrievalRequest",
    "RetrievalResponse",
    "RetrievalResult",
    "SecurityClassification",
    "ScoreTrace",
    "SourceReference",
    "SourceType",
]
