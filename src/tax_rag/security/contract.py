"""Security contract for retrieval-time RBAC enforcement."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class RetrievalEnforcementStage(StrEnum):
    PRE_RETRIEVAL = "pre_retrieval"

    @classmethod
    def from_value(cls, value: str) -> "RetrievalEnforcementStage":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(
                "RBAC enforcement must be 'pre_retrieval' so unauthorized chunks never enter scoring or ranking. "
                f"Got: {value}"
            ) from exc


class ProtectedRetrievalSurface(StrEnum):
    LEXICAL = "lexical"
    DENSE = "dense"
    FUSION = "fusion"
    RERANKING = "reranking"
    GENERATION = "generation"
    CACHE = "cache"
    EVALUATION = "evaluation"


@dataclass(frozen=True)
class RetrievalSecurityContract:
    enforcement_stage: RetrievalEnforcementStage = RetrievalEnforcementStage.PRE_RETRIEVAL
    deny_if_role_missing: bool = True
    deny_if_allowed_roles_missing: bool = True
    protected_surfaces: tuple[ProtectedRetrievalSurface, ...] = field(
        default_factory=lambda: (
            ProtectedRetrievalSurface.LEXICAL,
            ProtectedRetrievalSurface.DENSE,
            ProtectedRetrievalSurface.FUSION,
            ProtectedRetrievalSurface.RERANKING,
            ProtectedRetrievalSurface.GENERATION,
            ProtectedRetrievalSurface.CACHE,
            ProtectedRetrievalSurface.EVALUATION,
        )
    )

    def __post_init__(self) -> None:
        if self.enforcement_stage is not RetrievalEnforcementStage.PRE_RETRIEVAL:
            raise ValueError(
                "Only pre-retrieval RBAC enforcement is allowed. "
                "Unauthorized chunks must not influence retrieval, reranking, generation, caching, or evaluation."
            )
        if not self.protected_surfaces:
            raise ValueError("protected_surfaces must not be empty")


def validate_retrieval_enforcement_stage(
    value: str | RetrievalEnforcementStage,
) -> RetrievalEnforcementStage:
    if isinstance(value, RetrievalEnforcementStage):
        return value
    return RetrievalEnforcementStage.from_value(value)


DEFAULT_RETRIEVAL_SECURITY_CONTRACT = RetrievalSecurityContract()

