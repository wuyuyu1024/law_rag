"""Evaluation module for tax_rag."""

from tax_rag.eval.latency import LatencyBenchmarkRunner, run_latency_benchmark_from_paths
from tax_rag.eval.runner import EvalRunner, load_gold_cases, run_eval_from_paths
from tax_rag.eval.schemas import EvalCaseResult, EvalReport, GoldEvalCase, LatencyCaseResult, LatencyReport

__all__ = [
    "EvalCaseResult",
    "EvalReport",
    "EvalRunner",
    "GoldEvalCase",
    "LatencyBenchmarkRunner",
    "LatencyCaseResult",
    "LatencyReport",
    "load_gold_cases",
    "run_latency_benchmark_from_paths",
    "run_eval_from_paths",
]
