"""Deterministic evaluation runner for the local agent baseline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tax_rag.common import DEFAULT_CONFIG
from tax_rag.agent import CorrectiveRAGAgent
from tax_rag.retrieval import RetrievalService
from tax_rag.schemas import AnswerOutcome
from tax_rag.eval.schemas import (
    EvalCaseResult,
    EvalReport,
    EvalTraceRecord,
    GoldEvalCase,
    PromotionCheck,
    PromotionDecision,
)


def load_gold_cases(path: str | Path) -> tuple[GoldEvalCase, ...]:
    cases: list[GoldEvalCase] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        cases.append(GoldEvalCase.model_validate_json(line))
    return tuple(cases)


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def _citation_match_count(expected_substrings: tuple[str, ...], citations: tuple[str, ...]) -> int:
    if not expected_substrings:
        return 0
    normalized_citations = [_normalize_text(citation) for citation in citations]
    count = 0
    for needle in expected_substrings:
        normalized_needle = _normalize_text(needle)
        if any(normalized_needle in citation for citation in normalized_citations):
            count += 1
    return count


def _unauthorized_retrieval_failure(
    forbidden_substrings: tuple[str, ...],
    citations: tuple[str, ...],
    answer_text: str | None,
) -> bool:
    normalized_citations = [_normalize_text(citation) for citation in citations]
    normalized_answer = _normalize_text(answer_text or "")
    for needle in forbidden_substrings:
        normalized_needle = _normalize_text(needle)
        if any(normalized_needle in citation for citation in normalized_citations):
            return True
        if normalized_needle in normalized_answer:
            return True
    return False


def _faithfulness_proxy(answer_text: str | None, citations: tuple[str, ...], chunk_text_by_id: dict[str, str], chunk_ids: tuple[str, ...]) -> bool:
    if not answer_text or not citations or not chunk_ids:
        return False
    normalized_answer = _normalize_text(answer_text)
    for chunk_id in chunk_ids:
        chunk_text = chunk_text_by_id.get(chunk_id, "")
        normalized_chunk = _normalize_text(chunk_text)
        if len(normalized_chunk) >= 24 and normalized_chunk[:24] in normalized_answer:
            return True
    return False


def _report_metric(report: EvalReport, name: str) -> float | int:
    value = report.metrics[name]
    if isinstance(value, bool):
        return int(value)
    return value


def evaluate_promotion(
    candidate_report: EvalReport,
    *,
    baseline_report: EvalReport | None = None,
    candidate_label: str = "candidate",
) -> PromotionDecision:
    promotion = DEFAULT_CONFIG.evaluation.promotion
    checks: list[PromotionCheck] = []

    absolute_thresholds = (
        ("answerable_vs_refused_accuracy", ">=", promotion.min_answerable_vs_refused_accuracy),
        ("citation_presence_rate", ">=", promotion.min_citation_presence_rate),
        ("unauthorized_retrieval_failures", "<=", promotion.max_unauthorized_retrieval_failures),
        ("exact_lookup_success", ">=", promotion.min_exact_lookup_success),
        ("semantic_retrieval_success", ">=", promotion.min_semantic_retrieval_success),
        ("faithfulness_proxy", ">=", promotion.min_faithfulness_proxy),
        ("context_precision_proxy", ">=", promotion.min_context_precision_proxy),
    )
    for metric_name, comparator, expected in absolute_thresholds:
        actual = _report_metric(candidate_report, metric_name)
        passed = actual >= expected if comparator == ">=" else actual <= expected
        checks.append(
            PromotionCheck(
                name=metric_name,
                passed=passed,
                comparator=comparator,
                actual=actual,
                expected=expected,
            )
        )

    if baseline_report is not None:
        regression_thresholds = (
            ("answerable_vs_refused_accuracy", promotion.max_accuracy_regression),
            ("exact_lookup_success", promotion.max_exact_lookup_regression),
            ("semantic_retrieval_success", promotion.max_semantic_regression),
            ("context_precision_proxy", promotion.max_context_precision_regression),
        )
        for metric_name, tolerance in regression_thresholds:
            baseline_value = float(_report_metric(baseline_report, metric_name))
            candidate_value = float(_report_metric(candidate_report, metric_name))
            allowed_floor = baseline_value - tolerance
            checks.append(
                PromotionCheck(
                    name=f"{metric_name}_vs_baseline",
                    passed=candidate_value >= allowed_floor,
                    comparator=">=",
                    actual=candidate_value,
                    expected=allowed_floor,
                    details=f"baseline={baseline_value:.6f}, max_regression={tolerance:.6f}",
                )
            )

    return PromotionDecision(
        evaluated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        candidate_label=candidate_label,
        passed=all(check.passed for check in checks),
        checks=tuple(checks),
        metadata={
            "candidate_report_generated_at": candidate_report.generated_at,
            "baseline_report_generated_at": baseline_report.generated_at if baseline_report is not None else None,
        },
    )


@dataclass
class EvalRunner:
    retrieval_service: RetrievalService

    @property
    def agent(self) -> CorrectiveRAGAgent:
        return CorrectiveRAGAgent(self.retrieval_service)

    def run_case(self, case: GoldEvalCase) -> EvalCaseResult:
        response = self.agent.answer(case.query, case.role)
        citations = tuple(citation.citation_path for citation in response.citations)
        execution_trace = tuple(
            event for event in response.metadata.get("execution_trace", ()) if isinstance(event, dict)
        )
        expected_citation_match_count = _citation_match_count(case.expected_citation_substrings, citations)
        expected_citation_total = len(case.expected_citation_substrings)
        outcome_match = response.outcome is case.expected_outcome
        grade_match = case.expected_grade is None or response.evidence.grade is case.expected_grade
        refusal_reason_match = (
            case.expected_refusal_reason is None or response.evidence.refusal_reason is case.expected_refusal_reason
        )
        citation_presence = bool(response.citations)
        unauthorized_failure = _unauthorized_retrieval_failure(
            case.forbidden_citation_substrings,
            citations,
            response.answer_text,
        )
        chunk_text_by_id = {chunk.chunk_id: chunk.text for chunk in self.retrieval_service.chunks}
        faithfulness_pass = _faithfulness_proxy(
            response.answer_text,
            citations,
            chunk_text_by_id,
            tuple(citation.chunk_id for citation in response.citations),
        )
        context_precision_proxy = (
            expected_citation_match_count / expected_citation_total if expected_citation_total > 0 else 1.0
        )
        passed = (
            outcome_match
            and grade_match
            and refusal_reason_match
            and not unauthorized_failure
            and (expected_citation_total == 0 or expected_citation_match_count == expected_citation_total)
        )

        return EvalCaseResult(
            case_id=case.case_id,
            category=case.category,
            passed=passed,
            outcome_match=outcome_match,
            grade_match=grade_match,
            refusal_reason_match=refusal_reason_match,
            citation_presence=citation_presence,
            expected_citation_match_count=expected_citation_match_count,
            expected_citation_total=expected_citation_total,
            unauthorized_retrieval_failure=unauthorized_failure,
            faithfulness_proxy_pass=faithfulness_pass,
            context_precision_proxy=context_precision_proxy,
            query=case.query,
            role=case.role,
            expected_outcome=case.expected_outcome,
            actual_outcome=response.outcome,
            expected_grade=case.expected_grade,
            actual_grade=response.evidence.grade,
            expected_refusal_reason=case.expected_refusal_reason,
            actual_refusal_reason=response.evidence.refusal_reason,
            citations=citations,
            state_trace=response.state_trace,
            execution_trace=execution_trace,
            answer_text=response.answer_text,
            notes=case.notes,
        )

    def run_cases(self, cases: tuple[GoldEvalCase, ...]) -> EvalReport:
        results = tuple(self.run_case(case) for case in cases)
        total_cases = len(results)
        passed_cases = sum(1 for result in results if result.passed)
        answered_cases = [result for result in results if result.actual_outcome is AnswerOutcome.ANSWERED]
        exact_cases = [result for result in results if result.category == "exact_lookup"]
        semantic_cases = [result for result in results if result.category == "semantic_lookup"]
        unauthorized_cases = [result for result in results if result.category == "unauthorized_role"]

        metrics: dict[str, float | int] = {
            "answerable_vs_refused_accuracy": passed_cases / total_cases if total_cases else 0.0,
            "citation_presence_rate": (
                sum(1 for result in answered_cases if result.citation_presence) / len(answered_cases)
                if answered_cases
                else 0.0
            ),
            "unauthorized_retrieval_failures": sum(1 for result in unauthorized_cases if result.unauthorized_retrieval_failure),
            "exact_lookup_success": (
                sum(1 for result in exact_cases if result.passed) / len(exact_cases) if exact_cases else 0.0
            ),
            "semantic_retrieval_success": (
                sum(1 for result in semantic_cases if result.passed) / len(semantic_cases) if semantic_cases else 0.0
            ),
            "faithfulness_proxy": (
                sum(1 for result in answered_cases if result.faithfulness_proxy_pass) / len(answered_cases)
                if answered_cases
                else 0.0
            ),
            "context_precision_proxy": (
                sum(result.context_precision_proxy for result in results) / total_cases if total_cases else 0.0
            ),
        }

        return EvalReport(
            generated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            total_cases=total_cases,
            passed_cases=passed_cases,
            metrics=metrics,
            cases=results,
            metadata={"agent": "CorrectiveRAGAgent"},
        )

    def save_report(self, report: EvalReport, output_dir: str | Path) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        summary_path = output_dir / f"eval_report_{stamp}.json"
        details_path = output_dir / f"eval_cases_{stamp}.jsonl"
        traces_path = output_dir / f"eval_traces_{stamp}.jsonl"
        summary_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        details_path.write_text(
            "".join(f"{case.model_dump_json()}\n" for case in report.cases),
            encoding="utf-8",
        )
        if DEFAULT_CONFIG.evaluation.trace_output_enabled:
            traces_path.write_text(
                "".join(
                    f"{EvalTraceRecord(case_id=case.case_id, query=case.query, role=case.role, outcome=case.actual_outcome, evidence_grade=case.actual_grade, refusal_reason=case.actual_refusal_reason, state_trace=case.state_trace, execution_trace=case.execution_trace).model_dump_json()}\n"
                    for case in report.cases
                ),
                encoding="utf-8",
            )
        return summary_path


def run_eval_from_paths(
    *,
    chunks_path: str | Path,
    gold_path: str | Path,
    output_dir: str | Path,
    report_metadata: dict[str, Any] | None = None,
) -> EvalReport:
    runner = EvalRunner(RetrievalService.from_jsonl(str(chunks_path)))
    cases = load_gold_cases(gold_path)
    report = runner.run_cases(cases)
    if report_metadata:
        report = report.model_copy(update={"metadata": {**report.metadata, **report_metadata}})
    runner.save_report(report, output_dir)
    return report
