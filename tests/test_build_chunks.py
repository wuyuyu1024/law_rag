import json
from pathlib import Path

from tax_rag.chunking.pipeline import export_chunk_sets


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
