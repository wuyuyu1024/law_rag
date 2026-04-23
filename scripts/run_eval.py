#!/usr/bin/env python3
"""Run the local evaluation suite against the gold set."""

from __future__ import annotations

import argparse
from pathlib import Path

from tax_rag.eval import EvalReport, evaluate_promotion, run_eval_from_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local regression evaluation suite.")
    parser.add_argument("--chunks-path", default="data/chunks/legal_chunks.jsonl", help="Chunk JSONL used for retrieval")
    parser.add_argument("--gold-path", default="data/eval/gold_questions.jsonl", help="Gold evaluation JSONL")
    parser.add_argument("--output-dir", default="data/eval/eval_runs", help="Directory for eval outputs")
    parser.add_argument("--baseline-report", help="Prior eval report JSON used for non-regression promotion gating")
    parser.add_argument("--candidate-label", default="candidate", help="Label attached to the evaluated candidate")
    parser.add_argument("--embedding-model", help="Embedding model identifier recorded in the eval metadata")
    parser.add_argument("--reranker-model", help="Reranker identifier recorded in the eval metadata")
    parser.add_argument("--generator-model", help="Generator identifier recorded in the eval metadata")
    parser.add_argument("--gate-promotion", action="store_true", help="Apply promotion checks and exit non-zero on failure")
    args = parser.parse_args()

    report = run_eval_from_paths(
        chunks_path=args.chunks_path,
        gold_path=args.gold_path,
        output_dir=args.output_dir,
        report_metadata={
            "candidate_label": args.candidate_label,
            "embedding_model": args.embedding_model,
            "reranker_model": args.reranker_model,
            "generator_model": args.generator_model,
        },
    )

    print(f"Evaluated {report.total_cases} cases")
    print(f"Passed {report.passed_cases} cases")
    for metric_name, value in report.metrics.items():
        print(f"{metric_name}: {value}")

    if not args.gate_promotion:
        return 0

    baseline_report = None
    if args.baseline_report:
        baseline_report = EvalReport.model_validate_json(Path(args.baseline_report).read_text(encoding="utf-8"))
    decision = evaluate_promotion(
        report,
        baseline_report=baseline_report,
        candidate_label=args.candidate_label,
    )
    decision_path = Path(args.output_dir) / f"promotion_decision_{args.candidate_label}.json"
    decision_path.write_text(decision.model_dump_json(indent=2), encoding="utf-8")

    print(f"promotion_gate: {'passed' if decision.passed else 'failed'}")
    for check in decision.checks:
        print(
            f"- {check.name}: {'pass' if check.passed else 'fail'} "
            f"(actual={check.actual}, comparator={check.comparator}, expected={check.expected})"
        )
    return 0 if decision.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
