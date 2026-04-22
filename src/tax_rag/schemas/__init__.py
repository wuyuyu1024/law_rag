"""Typed contracts shared across modules."""

from tax_rag.schemas.answer import (
    AgentResponse,
    AnswerCitation,
    AnswerOutcome,
    EvidenceAssessment,
    EvidenceGrade,
    RefusalReason,
)
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
    "AgentResponse",
    "AnswerCitation",
    "AnswerOutcome",
    "ChunkRecord",
    "EvidenceAssessment",
    "EvidenceGrade",
    "NormalizedDocument",
    "RefusalReason",
    "RetrievalMethod",
    "RetrievalRequest",
    "RetrievalResponse",
    "RetrievalResult",
    "SecurityClassification",
    "ScoreTrace",
    "SourceReference",
    "SourceType",
]
