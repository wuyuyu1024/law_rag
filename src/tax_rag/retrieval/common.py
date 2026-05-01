"""Shared retrieval helpers for authorized candidate handling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re

from tax_rag.schemas import ChunkRecord, RetrievalRequest

_ISO_DATE_PATTERN = re.compile(r"\b(19|20)\d{2}-\d{2}-\d{2}\b")


@dataclass(frozen=True)
class RequestScopedChunks:
    chunks: tuple[ChunkRecord, ...]
    source_type_filtered_count: int = 0
    jurisdiction_filtered_count: int = 0
    validity_filtered_count: int = 0


def load_chunk_records(path: str | Path) -> list[ChunkRecord]:
    records: list[ChunkRecord] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(ChunkRecord.from_dict(json.loads(line)))
    return records


def infer_as_of_date(query: str) -> str | None:
    match = _ISO_DATE_PATTERN.search(query)
    return match.group(0) if match is not None else None


def chunk_valid_on(chunk: ChunkRecord, as_of_date: str | None) -> bool:
    if as_of_date is None:
        return True
    target = date.fromisoformat(as_of_date)
    if chunk.valid_from is not None and target < date.fromisoformat(chunk.valid_from):
        return False
    if chunk.valid_to is not None and target > date.fromisoformat(chunk.valid_to):
        return False
    return True


def request_allows_chunk(chunk: ChunkRecord, request: RetrievalRequest) -> bool:
    if request.source_types and chunk.source_type not in request.source_types:
        return False
    if request.jurisdiction is not None and chunk.jurisdiction != request.jurisdiction:
        return False
    if not chunk_valid_on(chunk, request.as_of_date):
        return False
    return True


def scope_chunks_for_request(
    chunks: list[ChunkRecord] | tuple[ChunkRecord, ...],
    request: RetrievalRequest,
) -> RequestScopedChunks:
    scoped: list[ChunkRecord] = []
    source_type_filtered_count = 0
    jurisdiction_filtered_count = 0
    validity_filtered_count = 0
    for chunk in chunks:
        if request.source_types and chunk.source_type not in request.source_types:
            source_type_filtered_count += 1
            continue
        if request.jurisdiction is not None and chunk.jurisdiction != request.jurisdiction:
            jurisdiction_filtered_count += 1
            continue
        if not chunk_valid_on(chunk, request.as_of_date):
            validity_filtered_count += 1
            continue
        scoped.append(chunk)
    return RequestScopedChunks(
        chunks=tuple(scoped),
        source_type_filtered_count=source_type_filtered_count,
        jurisdiction_filtered_count=jurisdiction_filtered_count,
        validity_filtered_count=validity_filtered_count,
    )
