"""Indexing module for tax_rag."""

from tax_rag.indexing.qdrant_local import DEFAULT_DENSE_COLLECTION_NAME, LocalQdrantIndex, ensure_local_qdrant_index

__all__ = [
    "DEFAULT_DENSE_COLLECTION_NAME",
    "LocalQdrantIndex",
    "ensure_local_qdrant_index",
]
