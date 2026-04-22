"""Shared retrieval helpers for authorized candidate handling."""

from __future__ import annotations

import json
from pathlib import Path

from tax_rag.schemas import ChunkRecord, RetrievalRequest


def load_chunk_records(path: str | Path) -> list[ChunkRecord]:
    records: list[ChunkRecord] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(ChunkRecord.from_dict(json.loads(line)))
    return records


def request_allows_chunk(chunk: ChunkRecord, request: RetrievalRequest) -> bool:
    if request.source_types and chunk.source_type not in request.source_types:
        return False
    if request.jurisdiction is not None and chunk.jurisdiction != request.jurisdiction:
        return False
    return True
