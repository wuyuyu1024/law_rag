"""Evaluation module for tax_rag."""

from tax_rag.eval.latency import LatencyBenchmarkRunner, run_latency_benchmark_from_paths
from tax_rag.eval.runner import (
    EvalRunner,
    evaluate_promotion,
    load_gold_cases,
    run_eval_from_paths,
)
from tax_rag.eval.schemas import (
    EvalCaseResult,
    EvalReport,
    EvalTraceRecord,
    GoldEvalCase,
    LatencyCaseResult,
    LatencyReport,
    PromotionCheck,
    PromotionDecision,
)

__all__ = [
    "EvalCaseResult",
    "EvalReport",
    "EvalRunner",
    "EvalTraceRecord",
    "GoldEvalCase",
    "LatencyBenchmarkRunner",
    "LatencyCaseResult",
    "LatencyReport",
    "load_gold_cases",
    "PromotionCheck",
    "PromotionDecision",
    "evaluate_promotion",
    "run_latency_benchmark_from_paths",
    "run_eval_from_paths",
]
