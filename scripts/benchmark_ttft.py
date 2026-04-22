#!/usr/bin/env python3
"""Benchmark the uncached request path against the TTFT target."""

from __future__ import annotations

import argparse

from tax_rag.eval import run_latency_benchmark_from_paths
from tax_rag.schemas import RetrievalMethod


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark the uncached local request path against the TTFT target.")
    parser.add_argument("--chunks-path", default="data/chunks/legal_chunks.jsonl", help="Chunk JSONL used for retrieval")
    parser.add_argument("--gold-path", default="data/eval/gold_questions.jsonl", help="Gold evaluation JSONL")
    parser.add_argument("--output-dir", default="data/eval/benchmark_runs", help="Directory for benchmark outputs")
    parser.add_argument("--dense-index-path", default=None, help="Optional persistent local Qdrant index directory")
    parser.add_argument("--dense-collection-name", default="dense_chunks", help="Persistent Qdrant collection name")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum number of gold cases to benchmark")
    parser.add_argument(
        "--method",
        choices=[member.value for member in RetrievalMethod],
        default=RetrievalMethod.HYBRID.value,
        help="Retrieval method used for the benchmark run",
    )
    parser.add_argument(
        "--target-ttft-ms",
        type=float,
        default=1500.0,
        help="Target uncached TTFT threshold in milliseconds",
    )
    args = parser.parse_args()

    report = run_latency_benchmark_from_paths(
        chunks_path=args.chunks_path,
        gold_path=args.gold_path,
        output_dir=args.output_dir,
        limit=args.limit,
        method=RetrievalMethod.from_value(args.method),
        target_ttft_ms=args.target_ttft_ms,
        dense_index_path=args.dense_index_path,
        dense_collection_name=args.dense_collection_name,
    )

    print(f"Benchmarked {report.total_cases} uncached cases")
    print(f"Cases under {report.target_ttft_ms} ms: {report.cases_under_target}")
    print(f"cache_enabled: {report.metadata['cache_enabled']}")
    for metric_name, value in report.metrics.items():
        print(f"{metric_name}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
