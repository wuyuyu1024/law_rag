#!/usr/bin/env python3
"""Run the local evaluation suite against the gold set."""

from __future__ import annotations

import argparse

from tax_rag.eval import run_eval_from_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local regression evaluation suite.")
    parser.add_argument("--chunks-path", default="data/chunks/legal_chunks.jsonl", help="Chunk JSONL used for retrieval")
    parser.add_argument("--gold-path", default="data/eval/gold_questions.jsonl", help="Gold evaluation JSONL")
    parser.add_argument("--output-dir", default="data/eval/eval_runs", help="Directory for eval outputs")
    args = parser.parse_args()

    report = run_eval_from_paths(
        chunks_path=args.chunks_path,
        gold_path=args.gold_path,
        output_dir=args.output_dir,
    )

    print(f"Evaluated {report.total_cases} cases")
    print(f"Passed {report.passed_cases} cases")
    for metric_name, value in report.metrics.items():
        print(f"{metric_name}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
