"""Normalization helpers for demo corpus sources.

The demo runtime currently uses public Dutch laws and case law.
Internal policy and e-learning/wiki sources are represented here by fixture-backed
adapters so the architecture matches the full assignment scope before those
sources are added to the runtime dataset.
"""

from __future__ import annotations

from tax_rag.schemas import NormalizedDocument, SecurityClassification, SourceType


def normalize_policy_fixture(
    *,
    doc_id: str,
    title: str,
    text: str,
    source_path: str,
    security_classification: str = "internal",
    allowed_roles: tuple[str, ...] = ("inspector", "legal_counsel"),
) -> NormalizedDocument:
    return NormalizedDocument(
        doc_id=doc_id,
        source_type=SourceType.INTERNAL_POLICY,
        title=title,
        jurisdiction="NL",
        text=text,
        source_path=source_path,
        citation_path=title,
        security_classification=SecurityClassification(security_classification),
        allowed_roles=allowed_roles,
        metadata={"simulated_source": True},
    )


def normalize_e_learning_fixture(
    *,
    doc_id: str,
    title: str,
    text: str,
    source_path: str,
    allowed_roles: tuple[str, ...] = ("helpdesk", "inspector", "legal_counsel"),
) -> NormalizedDocument:
    return NormalizedDocument(
        doc_id=doc_id,
        source_type=SourceType.E_LEARNING,
        title=title,
        jurisdiction="NL",
        text=text,
        source_path=source_path,
        citation_path=title,
        allowed_roles=allowed_roles,
        metadata={"simulated_source": True},
    )
