from tax_rag.schemas import ChunkRecord, SecurityClassification, SourceType
from tax_rag.security import evaluate_chunk_access, filter_authorized_chunks


def _chunk(
    *,
    chunk_id: str,
    allowed_roles: tuple[str, ...],
    security_classification: SecurityClassification,
) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=chunk_id,
        doc_id=f"doc:{chunk_id}",
        text=f"Text for {chunk_id}",
        citation_path=f"Citation for {chunk_id}",
        source_type=SourceType.INTERNAL_POLICY,
        jurisdiction="NL",
        allowed_roles=allowed_roles,
        source_path=f"fixtures/{chunk_id}.md",
        security_classification=security_classification,
    )


def test_evaluate_chunk_access_requires_role_membership_before_retrieval() -> None:
    decision = evaluate_chunk_access(
        _chunk(
            chunk_id="restricted-policy",
            allowed_roles=("inspector", "legal_counsel"),
            security_classification=SecurityClassification.RESTRICTED,
        ),
        role="helpdesk",
    )

    assert decision.allowed is False
    assert decision.reason == "role_not_permitted"


def test_evaluate_chunk_access_applies_classification_clearance() -> None:
    decision = evaluate_chunk_access(
        _chunk(
            chunk_id="confidential-training",
            allowed_roles=("helpdesk", "inspector"),
            security_classification=SecurityClassification.CONFIDENTIAL,
        ),
        role="helpdesk",
    )

    assert decision.allowed is False
    assert decision.reason == "classification_exceeds_role_clearance"


def test_filter_authorized_chunks_returns_only_authorized_candidates() -> None:
    public_chunk = _chunk(
        chunk_id="public-guidance",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
    )
    internal_chunk = _chunk(
        chunk_id="internal-training",
        allowed_roles=("helpdesk", "inspector"),
        security_classification=SecurityClassification.INTERNAL,
    )
    restricted_chunk = _chunk(
        chunk_id="restricted-fraud",
        allowed_roles=("inspector", "legal_counsel"),
        security_classification=SecurityClassification.RESTRICTED,
    )

    filtered = filter_authorized_chunks([public_chunk, internal_chunk, restricted_chunk], role="helpdesk")

    assert filtered.enforcement_stage == "pre_retrieval"
    assert [chunk.chunk_id for chunk in filtered.authorized_chunks] == ["public-guidance", "internal-training"]
    assert filtered.denied_count == 1
    assert any(
        decision.chunk_id == "restricted-fraud" and decision.reason == "role_not_permitted"
        for decision in filtered.decisions
    )


def test_filter_authorized_chunks_denies_unknown_roles_in_strict_mode() -> None:
    filtered = filter_authorized_chunks(
        [
            _chunk(
                chunk_id="public-guidance",
                allowed_roles=("helpdesk", "inspector", "legal_counsel"),
                security_classification=SecurityClassification.PUBLIC,
            )
        ],
        role="contractor",
    )

    assert filtered.authorized_chunks == ()
    assert filtered.decisions[0].allowed is False
    assert filtered.decisions[0].reason == "unknown_role"
