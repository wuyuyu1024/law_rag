"""Merge parsed source files into a unified JSONL dataset."""

from __future__ import annotations

import json
from pathlib import Path


def merge_jsonl_files(input_paths: list[str | Path], output_path: str | Path) -> int:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    seen_ids: set[str] = set()
    written = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for input_path in [Path(path) for path in input_paths]:
            if not input_path.exists():
                continue
            for raw_line in input_path.read_text(encoding="utf-8").splitlines():
                if not raw_line.strip():
                    continue
                payload = json.loads(raw_line)
                doc_id = payload["doc_id"]
                if doc_id in seen_ids:
                    continue
                seen_ids.add(doc_id)
                handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
                written += 1
    return written
