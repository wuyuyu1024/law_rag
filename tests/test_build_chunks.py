import json
from pathlib import Path

from tax_rag.chunking.pipeline import export_chunk_sets


def test_export_chunk_sets_writes_expected_outputs(tmp_path: Path) -> None:
    parsed_dir = Path("data/parsed")
    chunks_dir = tmp_path / "chunks"

    counts = export_chunk_sets(
        laws_path=parsed_dir / "laws.jsonl",
        cases_path=parsed_dir / "cases.jsonl",
        policies_path=parsed_dir / "policies.jsonl",
        e_learning_path=parsed_dir / "e_learning.jsonl",
        laws_out=chunks_dir / "laws_chunks.jsonl",
        cases_out=chunks_dir / "case_chunks.jsonl",
        policies_out=chunks_dir / "policies_chunks.jsonl",
        e_learning_out=chunks_dir / "e_learning_chunks.jsonl",
        merged_out=chunks_dir / "legal_chunks.jsonl",
    )

    assert counts["laws"] > 0
    assert counts["cases"] > 0
    assert counts["policies"] > 0
    assert counts["e_learning"] > 0
    assert counts["merged"] == counts["laws"] + counts["cases"] + counts["policies"] + counts["e_learning"]

    merged_lines = (chunks_dir / "legal_chunks.jsonl").read_text(encoding="utf-8").splitlines()
    first_payload = json.loads(merged_lines[0])

    assert first_payload["chunk_id"]
    assert first_payload["doc_id"]
    assert first_payload["citation_path"]
    assert first_payload["source_type"] in {"legislation", "case_law", "internal_policy", "e_learning"}
    assert (chunks_dir / "policies_chunks.jsonl").exists()
    assert (chunks_dir / "e_learning_chunks.jsonl").exists()


def test_export_chunk_sets_records_include_required_chunk_fields(tmp_path: Path) -> None:
    parsed_dir = Path("data/parsed")
    chunks_dir = tmp_path / "chunks"

    export_chunk_sets(
        laws_path=parsed_dir / "laws.jsonl",
        cases_path=parsed_dir / "cases.jsonl",
        policies_path=parsed_dir / "policies.jsonl",
        e_learning_path=parsed_dir / "e_learning.jsonl",
        laws_out=chunks_dir / "laws_chunks.jsonl",
        cases_out=chunks_dir / "case_chunks.jsonl",
        policies_out=chunks_dir / "policies_chunks.jsonl",
        e_learning_out=chunks_dir / "e_learning_chunks.jsonl",
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
        assert payload["source_type"] in {"legislation", "case_law", "internal_policy", "e_learning"}
        assert payload["jurisdiction"]
        assert payload["allowed_roles"]
