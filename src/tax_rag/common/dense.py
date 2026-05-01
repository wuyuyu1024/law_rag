"""Shared dense retrieval helpers used by indexing and querying paths."""

from __future__ import annotations

import hashlib
import math
from typing import Any

from tax_rag.schemas import ChunkRecord, SecurityClassification

CLASSIFICATION_ORDER = {
    SecurityClassification.PUBLIC: 0,
    SecurityClassification.INTERNAL: 1,
    SecurityClassification.CONFIDENTIAL: 2,
    SecurityClassification.RESTRICTED: 3,
}


def _character_ngrams(token: str, size: int = 3) -> list[str]:
    normalized = token.replace(" ", "")
    if len(normalized) < size:
        return [normalized]
    return [normalized[index : index + size] for index in range(len(normalized) - size + 1)]


def _hashed_index(token: str, dimensions: int) -> int:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).hexdigest()
    return int(digest, 16) % dimensions


def embed_text(value: str, *, dimensions: int = 256) -> list[float]:
    from tax_rag.retrieval.semantic import semantic_features

    weights = [0.0] * dimensions
    for feature, weight in semantic_features(value).items():
        token_index = _hashed_index(f"tok:{feature}", dimensions)
        weights[token_index] += weight
        gram_token = feature.replace("concept:", "").replace("_", "")
        for gram in _character_ngrams(gram_token):
            gram_index = _hashed_index(f"tri:{gram}", dimensions)
            weights[gram_index] += 0.2 * weight

    norm = math.sqrt(sum(weight * weight for weight in weights))
    if norm == 0.0:
        return weights
    return [weight / norm for weight in weights]


def dense_text(chunk: ChunkRecord) -> str:
    return " ".join(
        part
        for part in (
            chunk.citation_path,
            chunk.text,
            chunk.article or "",
            chunk.ecli or "",
            chunk.section_type or "",
            chunk.source_type.value,
        )
        if part
    )


def payload_for_chunk(chunk: ChunkRecord) -> dict[str, Any]:
    return {
        "chunk": chunk.to_dict(),
        "allowed_roles": list(chunk.allowed_roles),
        "source_type": chunk.source_type.value,
        "jurisdiction": chunk.jurisdiction,
        "security_classification": chunk.security_classification.value,
        "security_classification_rank": CLASSIFICATION_ORDER[chunk.security_classification],
        "valid_from": chunk.valid_from,
        "valid_to": chunk.valid_to,
        "article": chunk.article,
        "ecli": chunk.ecli,
    }
