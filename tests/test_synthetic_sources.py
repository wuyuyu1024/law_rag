from pathlib import Path

from tax_rag.chunking import chunk_support_document
from tax_rag.ingestion.synthetic_sources import (
    parse_e_learning_fixture,
    parse_policy_fixture,
)
from tax_rag.schemas import SecurityClassification, SourceType


POLICY_PATH = Path("data/raw/internal_policy/fraud_signal_triage.json")
E_LEARNING_PATH = Path("data/raw/e_learning/vat_onboarding.json")


def test_parse_policy_fixture_preserves_security_and_roles() -> None:
    document = parse_policy_fixture(POLICY_PATH)

    assert document.source_type is SourceType.INTERNAL_POLICY
    assert document.security_classification is SecurityClassification.RESTRICTED
    assert document.allowed_roles == ("inspector", "legal_counsel")
    assert document.metadata["synthetic_fixture"] is True


def test_parse_e_learning_fixture_uses_fixture_source_path() -> None:
    document = parse_e_learning_fixture(E_LEARNING_PATH)

    assert document.source_type is SourceType.E_LEARNING
    assert document.source_path == str(E_LEARNING_PATH)
    assert "helpdesk" in document.allowed_roles
    assert document.metadata["simulated_source"] is True


def test_chunk_support_document_splits_policy_sections() -> None:
    document = parse_policy_fixture(POLICY_PATH)

    chunks = chunk_support_document(document)

    assert len(chunks) >= 4
    assert chunks[0].citation_path.endswith("> Scope")
    assert all(chunk.doc_id == document.doc_id for chunk in chunks)
    assert all(chunk.source_type is SourceType.INTERNAL_POLICY for chunk in chunks)


def test_chunk_support_document_splits_e_learning_sections() -> None:
    document = parse_e_learning_fixture(E_LEARNING_PATH)

    chunks = chunk_support_document(document)
    escalation_chunk = next(chunk for chunk in chunks if chunk.metadata["section_title"] == "When To Escalate")

    assert escalation_chunk.citation_path.endswith("> When To Escalate")
    assert "multiple legal sources" in escalation_chunk.text
    assert escalation_chunk.allowed_roles == document.allowed_roles
