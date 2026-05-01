#!/usr/bin/env python3
"""Minimal CLI demo for answer/refusal inspection."""

from __future__ import annotations

import argparse

from tax_rag.app import format_agent_response, run_demo_query
from tax_rag.schemas import RetrievalMethod


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the minimal tax_rag CLI demo.")
    parser.add_argument(
        "--chunks-path", default="data/chunks/legal_chunks.jsonl", help="Chunk JSONL used for retrieval"
    )
    parser.add_argument("--query", required=True, help="Question to run through the demo agent")
    parser.add_argument("--role", default="helpdesk", help="Role used for RBAC-constrained retrieval")
    parser.add_argument(
        "--method",
        choices=[member.value for member in RetrievalMethod],
        default=RetrievalMethod.HYBRID.value,
        help="Retrieval method used for the demo query",
    )
    parser.add_argument("--dense-index-path", default=None, help="Optional persistent local Qdrant index directory")
    parser.add_argument("--dense-collection-name", default="dense_chunks", help="Persistent Qdrant collection name")
    parser.add_argument(
        "--cache-backend",
        choices=("none", "in_memory", "redis"),
        default=None,
        help="Optional semantic cache backend for answer-level caching",
    )
    args = parser.parse_args()

    response = run_demo_query(
        chunks_path=args.chunks_path,
        query=args.query,
        role=args.role,
        method=RetrievalMethod.from_value(args.method),
        dense_index_path=args.dense_index_path,
        dense_collection_name=args.dense_collection_name,
        cache_backend=args.cache_backend,
    )
    print(format_agent_response(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
