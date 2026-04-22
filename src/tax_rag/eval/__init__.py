"""Evaluation module for tax_rag."""

from tax_rag.eval.runner import EvalRunner, load_gold_cases, run_eval_from_paths
from tax_rag.eval.schemas import EvalCaseResult, EvalReport, GoldEvalCase

__all__ = [
    "EvalCaseResult",
    "EvalReport",
    "EvalRunner",
    "GoldEvalCase",
    "load_gold_cases",
    "run_eval_from_paths",
]
