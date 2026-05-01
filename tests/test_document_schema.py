import pytest
from pydantic import ValidationError

from tax_rag.ingestion.normalizer import (
    normalize_e_learning_fixture,
    normalize_policy_fixture,
)
from tax_rag.schemas import SecurityClassification, SourceType
from tax_rag.schemas import ChunkRecord, NormalizedDocument


def test_source_type_rejects_unsupported_values() -> None:
    with pytest.raises(ValueError):
        SourceType.from_value("blog_post")


def test_fixture_adapters_cover_non_demo_source_types() -> None:
    policy = normalize_policy_fixture(
        doc_id="policy:demo:1",
        title="Internal Fraud Memo",
        text="Restricted internal guidance.",
        source_path="fixtures/policy/internal_fraud_memo.md",
    )
    wiki = normalize_e_learning_fixture(
        doc_id="wiki:demo:1",
        title="VAT Onboarding Module",
        text="Helpdesk onboarding content.",
        source_path="fixtures/wiki/vat_onboarding.md",
    )

    assert policy.source_type is SourceType.INTERNAL_POLICY
    assert policy.security_classification is SecurityClassification.INTERNAL
    assert wiki.source_type is SourceType.E_LEARNING
    assert wiki.metadata["simulated_source"] is True


def test_document_and_chunk_validity_ranges_are_validated() -> None:
    with pytest.raises(ValidationError):
        NormalizedDocument(
            doc_id="law:invalid",
            source_type=SourceType.LEGISLATION,
            title="Invalid Law",
            jurisdiction="NL",
            text="Text",
            source_path="fixtures/law.xml",
            valid_from="2026-01-01",
            valid_to="2025-12-31",
        )

    chunk = ChunkRecord(
        chunk_id="law:valid",
        doc_id="law:valid",
        text="Text",
        citation_path="Valid Law > Artikel 1",
        source_type=SourceType.LEGISLATION,
        jurisdiction="NL",
        allowed_roles=("helpdesk",),
        source_path="fixtures/law.xml",
        valid_from="2025-01-01",
        valid_to="2026-01-01",
    )

    assert chunk.valid_from == "2025-01-01"
