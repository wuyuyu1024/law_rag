"""Chunk export pipeline for parsed legal documents."""

from __future__ import annotations

import json
from pathlib import Path

from tax_rag.chunking.case_chunker import chunk_case_document
from tax_rag.chunking.legal_chunker import chunk_law_document
from tax_rag.schemas import ChunkRecord, NormalizedDocument, SourceType

SUPPORTED_CHUNK_SOURCE_TYPES = {
    SourceType.LEGISLATION,
    SourceType.CASE_LAW,
}


def load_documents(path: str | Path) -> list[NormalizedDocument]:
    records: list[NormalizedDocument] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(NormalizedDocument.from_dict(json.loads(line)))
    return records


def build_chunks(documents: list[NormalizedDocument]) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    for document in documents:
        if document.source_type is SourceType.LEGISLATION:
            chunks.extend(chunk_law_document(document))
        elif document.source_type is SourceType.CASE_LAW:
            chunks.extend(chunk_case_document(document))
        else:
            supported = ", ".join(sorted(source_type.value for source_type in SUPPORTED_CHUNK_SOURCE_TYPES))
            raise ValueError(
                "Unsupported source type for chunking "
                f"'{document.source_type.value}' for doc_id '{document.doc_id}'. "
                f"Supported types: {supported}"
            )
    return chunks


def write_chunks(path: str | Path, chunks: list[ChunkRecord]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"{chunk.to_json()}\n" for chunk in chunks),
        encoding="utf-8",
    )


def export_chunk_sets(
    *,
    laws_path: str | Path,
    cases_path: str | Path,
    laws_out: str | Path,
    cases_out: str | Path,
    merged_out: str | Path,
) -> tuple[int, int, int]:
    law_chunks = build_chunks(load_documents(laws_path))
    case_chunks = build_chunks(load_documents(cases_path))
    merged_chunks = [*law_chunks, *case_chunks]

    write_chunks(laws_out, law_chunks)
    write_chunks(cases_out, case_chunks)
    write_chunks(merged_out, merged_chunks)

    return len(law_chunks), len(case_chunks), len(merged_chunks)
