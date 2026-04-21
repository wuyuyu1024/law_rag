import pytest

from tax_rag.ingestion.normalizer import (
    normalize_e_learning_fixture,
    normalize_policy_fixture,
)
from tax_rag.schemas import SecurityClassification, SourceType


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
