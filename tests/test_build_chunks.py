import json
from pathlib import Path

import pytest

from tax_rag.chunking.pipeline import export_chunk_sets
from tax_rag.chunking.pipeline import build_chunks
from tax_rag.ingestion.normalizer import normalize_policy_fixture


def test_export_chunk_sets_writes_expected_outputs(tmp_path: Path) -> None:
    parsed_dir = Path("data/parsed")
    chunks_dir = tmp_path / "chunks"

    law_count, case_count, merged_count = export_chunk_sets(
        laws_path=parsed_dir / "laws.jsonl",
        cases_path=parsed_dir / "cases.jsonl",
        laws_out=chunks_dir / "laws_chunks.jsonl",
        cases_out=chunks_dir / "case_chunks.jsonl",
        merged_out=chunks_dir / "legal_chunks.jsonl",
    )

    assert law_count > 0
    assert case_count > 0
    assert merged_count == law_count + case_count

    merged_lines = (chunks_dir / "legal_chunks.jsonl").read_text(encoding="utf-8").splitlines()
    first_payload = json.loads(merged_lines[0])

    assert first_payload["chunk_id"]
    assert first_payload["doc_id"]
    assert first_payload["citation_path"]
    assert first_payload["source_type"] in {"legislation", "case_law"}


def test_export_chunk_sets_records_include_required_chunk_fields(tmp_path: Path) -> None:
    parsed_dir = Path("data/parsed")
    chunks_dir = tmp_path / "chunks"

    export_chunk_sets(
        laws_path=parsed_dir / "laws.jsonl",
        cases_path=parsed_dir / "cases.jsonl",
        laws_out=chunks_dir / "laws_chunks.jsonl",
        cases_out=chunks_dir / "case_chunks.jsonl",
        merged_out=chunks_dir / "legal_chunks.jsonl",
    )

    required_fields = {
        "allowed_roles",
        "chunk_id",
        "citation_path",
        "doc_id",
        "jurisdiction",
        "source_type",
        "text",
    }
    merged_lines = (chunks_dir / "legal_chunks.jsonl").read_text(encoding="utf-8").splitlines()

    for line in merged_lines:
        payload = json.loads(line)
        assert required_fields <= payload.keys()
        assert payload["chunk_id"]
        assert payload["doc_id"]
        assert payload["text"]
        assert payload["citation_path"]
        assert payload["source_type"] in {"legislation", "case_law"}
        assert payload["jurisdiction"]
        assert payload["allowed_roles"]


def test_build_chunks_rejects_unsupported_source_types() -> None:
    document = normalize_policy_fixture(
        doc_id="policy:demo:chunking",
        title="Internal Memo",
        text="Restricted internal guidance.",
        source_path="fixtures/policy/internal_memo.md",
    )

    with pytest.raises(ValueError, match="Unsupported source type for chunking 'internal_policy'"):
        build_chunks([document])
