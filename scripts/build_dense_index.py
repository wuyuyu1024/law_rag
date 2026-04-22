#!/usr/bin/env python3
"""Build or rebuild the persistent local Qdrant dense index."""

from __future__ import annotations

import argparse

from tax_rag.indexing import ensure_local_qdrant_index
from tax_rag.retrieval import load_chunk_records


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the persistent local Qdrant dense index from chunk JSONL.")
    parser.add_argument("--chunks-path", default="data/chunks/legal_chunks.jsonl", help="Chunk JSONL used for indexing")
    parser.add_argument("--index-path", default="data/indexes/qdrant", help="Directory for the local persistent Qdrant store")
    parser.add_argument("--collection-name", default="dense_chunks", help="Collection name inside the local Qdrant store")
    parser.add_argument("--recreate", action="store_true", help="Delete and rebuild the collection if it already exists")
    args = parser.parse_args()

    chunks = load_chunk_records(args.chunks_path)
    result = ensure_local_qdrant_index(
        chunks,
        path=args.index_path,
        collection_name=args.collection_name,
        recreate=args.recreate,
    )
    print(f"path: {result['path']}")
    print(f"collection_name: {result['collection_name']}")
    print(f"created: {result['created']}")
    print(f"point_count: {result['point_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
