"""Helpers for clearly labeled synthetic stress-mode expansion."""

from __future__ import annotations

from tax_rag.schemas import ChunkRecord


def expand_chunks_for_stress(
    chunks: list[ChunkRecord] | tuple[ChunkRecord, ...],
    *,
    multiplier: int = 1,
) -> list[ChunkRecord]:
    if multiplier <= 1:
        return list(chunks)

    expanded: list[ChunkRecord] = []
    for replica_index in range(multiplier):
        replica_label = f"stress:{replica_index + 1}"
        for chunk in chunks:
            expanded.append(
                chunk.model_copy(
                    update={
                        "chunk_id": f"{chunk.chunk_id}::{replica_label}",
                        "doc_id": f"{chunk.doc_id}::{replica_label}",
                        "metadata": {
                            **chunk.metadata,
                            "synthetic_stress": True,
                            "stress_replica": replica_index + 1,
                            "stress_multiplier": multiplier,
                        },
                    }
                )
            )
    return expanded
