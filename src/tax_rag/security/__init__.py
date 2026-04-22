"""Security module for tax_rag."""

from tax_rag.security.contract import (
    DEFAULT_RETRIEVAL_SECURITY_CONTRACT,
    ProtectedRetrievalSurface,
    RetrievalEnforcementStage,
    RetrievalSecurityContract,
    validate_retrieval_enforcement_stage,
)
from tax_rag.security.rbac import (
    DEFAULT_ROLE_CLASSIFICATION_CLEARANCE,
    AccessDecision,
    AuthorizedChunkSet,
    evaluate_chunk_access,
    filter_authorized_chunks,
)

__all__ = [
    "DEFAULT_RETRIEVAL_SECURITY_CONTRACT",
    "DEFAULT_ROLE_CLASSIFICATION_CLEARANCE",
    "ProtectedRetrievalSurface",
    "RetrievalEnforcementStage",
    "RetrievalSecurityContract",
    "AccessDecision",
    "AuthorizedChunkSet",
    "evaluate_chunk_access",
    "filter_authorized_chunks",
    "validate_retrieval_enforcement_stage",
]
