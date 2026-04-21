import json
from pathlib import Path

from tax_rag.ingestion.merge_documents import merge_jsonl_files


def test_merge_jsonl_files_deduplicates_doc_ids(tmp_path: Path) -> None:
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    merged = tmp_path / "documents.jsonl"

    first.write_text(
        json.dumps({"doc_id": "a", "title": "one"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    second.write_text(
        "\n".join(
            [
                json.dumps({"doc_id": "a", "title": "duplicate"}, ensure_ascii=False),
                json.dumps({"doc_id": "b", "title": "two"}, ensure_ascii=False),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    written = merge_jsonl_files([first, second], merged)
    lines = merged.read_text(encoding="utf-8").splitlines()

    assert written == 2
    assert len(lines) == 2
