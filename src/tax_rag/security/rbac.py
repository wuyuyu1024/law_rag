"""Pre-retrieval RBAC filtering primitives for chunk authorization."""

from __future__ import annotations

from dataclasses import dataclass

from tax_rag.schemas import ChunkRecord, SecurityClassification
from tax_rag.security.contract import DEFAULT_RETRIEVAL_SECURITY_CONTRACT, RetrievalSecurityContract


@dataclass(frozen=True)
class AccessDecision:
    chunk_id: str
    role: str
    allowed: bool
    reason: str


@dataclass(frozen=True)
class AuthorizedChunkSet:
    role: str
    enforcement_stage: str
    authorized_chunks: tuple[ChunkRecord, ...]
    decisions: tuple[AccessDecision, ...]

    @property
    def denied_count(self) -> int:
        return sum(1 for decision in self.decisions if not decision.allowed)

    @property
    def authorized_count(self) -> int:
        return len(self.authorized_chunks)


_CLASSIFICATION_ORDER = {
    SecurityClassification.PUBLIC: 0,
    SecurityClassification.INTERNAL: 1,
    SecurityClassification.CONFIDENTIAL: 2,
    SecurityClassification.RESTRICTED: 3,
}

DEFAULT_ROLE_CLASSIFICATION_CLEARANCE: dict[str, SecurityClassification] = {
    "helpdesk": SecurityClassification.INTERNAL,
    "inspector": SecurityClassification.RESTRICTED,
    "legal_counsel": SecurityClassification.RESTRICTED,
}


def _classification_allowed(
    chunk: ChunkRecord,
    *,
    role: str,
    role_clearances: dict[str, SecurityClassification],
) -> bool:
    role_clearance = role_clearances.get(role)
    if role_clearance is None:
        return False
    return _CLASSIFICATION_ORDER[chunk.security_classification] <= _CLASSIFICATION_ORDER[role_clearance]


def evaluate_chunk_access(
    chunk: ChunkRecord,
    *,
    role: str,
    contract: RetrievalSecurityContract = DEFAULT_RETRIEVAL_SECURITY_CONTRACT,
    role_clearances: dict[str, SecurityClassification] | None = None,
) -> AccessDecision:
    role_clearances = role_clearances or DEFAULT_ROLE_CLASSIFICATION_CLEARANCE

    if contract.deny_if_role_missing and role not in role_clearances:
        return AccessDecision(
            chunk_id=chunk.chunk_id,
            role=role,
            allowed=False,
            reason="unknown_role",
        )

    if contract.deny_if_allowed_roles_missing and not chunk.allowed_roles:
        return AccessDecision(
            chunk_id=chunk.chunk_id,
            role=role,
            allowed=False,
            reason="missing_allowed_roles",
        )

    if role not in chunk.allowed_roles:
        return AccessDecision(
            chunk_id=chunk.chunk_id,
            role=role,
            allowed=False,
            reason="role_not_permitted",
        )

    if not _classification_allowed(chunk, role=role, role_clearances=role_clearances):
        return AccessDecision(
            chunk_id=chunk.chunk_id,
            role=role,
            allowed=False,
            reason="classification_exceeds_role_clearance",
        )

    return AccessDecision(
        chunk_id=chunk.chunk_id,
        role=role,
        allowed=True,
        reason="authorized",
    )


def filter_authorized_chunks(
    chunks: list[ChunkRecord] | tuple[ChunkRecord, ...],
    *,
    role: str,
    contract: RetrievalSecurityContract = DEFAULT_RETRIEVAL_SECURITY_CONTRACT,
    role_clearances: dict[str, SecurityClassification] | None = None,
) -> AuthorizedChunkSet:
    decisions = tuple(
        evaluate_chunk_access(
            chunk,
            role=role,
            contract=contract,
            role_clearances=role_clearances,
        )
        for chunk in chunks
    )
    allowed_chunk_ids = {decision.chunk_id for decision in decisions if decision.allowed}
    authorized_chunks = tuple(chunk for chunk in chunks if chunk.chunk_id in allowed_chunk_ids)

    return AuthorizedChunkSet(
        role=role,
        enforcement_stage=contract.enforcement_stage.value,
        authorized_chunks=authorized_chunks,
        decisions=decisions,
    )
