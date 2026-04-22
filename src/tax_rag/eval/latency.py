"""Latency benchmark harness for the uncached local baseline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from tax_rag.agent import build_agent_response, grade_evidence
from tax_rag.agent.transform import transform_query
from tax_rag.eval.runner import load_gold_cases
from tax_rag.eval.schemas import GoldEvalCase, LatencyCaseResult, LatencyReport
from tax_rag.retrieval import RetrievalMethod, RetrievalService

_REQUIRED_STAGE_KEYS = (
    "request_setup_ms",
    "request_scoping_ms",
    "security_filter_ms",
    "lexical_retrieval_ms",
    "dense_retrieval_ms",
    "fusion_ms",
    "reranking_ms",
    "retrieval_total_ms",
    "evidence_grading_ms",
    "answer_construction_ms",
    "total_uncached_ms",
)


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 3)


def _coerce_stage_timings(payload: dict[str, object] | None) -> dict[str, float]:
    timings = {key: 0.0 for key in _REQUIRED_STAGE_KEYS}
    if not payload:
        return timings
    for key, value in payload.items():
        if key not in timings:
            continue
        if isinstance(value, int | float):
            timings[key] = round(float(value), 3)
    return timings


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    index = round((len(ordered) - 1) * quantile)
    return round(ordered[index], 3)


@dataclass
class LatencyBenchmarkRunner:
    retrieval_service: RetrievalService
    target_ttft_ms: float = 1500.0
    cache_enabled: bool = False

    def run_case(
        self,
        case: GoldEvalCase,
        *,
        method: RetrievalMethod = RetrievalMethod.HYBRID,
    ) -> LatencyCaseResult:
        total_start = perf_counter()
        request_setup_start = perf_counter()
        transform_plan = transform_query(case.query)
        request_setup_ms = _elapsed_ms(request_setup_start)

        retrieval_response = self.retrieval_service.retrieve(
            query=case.query,
            role=case.role,
            method=method,
        )
        stage_timings = _coerce_stage_timings(retrieval_response.metadata.get("timings_ms"))
        stage_timings["request_setup_ms"] = request_setup_ms

        grading_start = perf_counter()
        evidence = grade_evidence(retrieval_response)
        stage_timings["evidence_grading_ms"] = _elapsed_ms(grading_start)

        answer_start = perf_counter()
        response = build_agent_response(
            query=case.query,
            role=case.role,
            retrieval_response=retrieval_response,
            evidence=evidence,
        )
        stage_timings["answer_construction_ms"] = _elapsed_ms(answer_start)

        total_uncached_ms = _elapsed_ms(total_start)
        stage_timings["total_uncached_ms"] = total_uncached_ms

        return LatencyCaseResult(
            case_id=case.case_id,
            category=case.category,
            query=case.query,
            role=case.role,
            retrieval_method=response.retrieval_method,
            outcome=response.outcome,
            evidence_grade=response.evidence.grade,
            transform_strategy=transform_plan.strategy.value,
            cache_enabled=self.cache_enabled,
            retrieval_result_count=len(retrieval_response.results),
            target_ttft_ms=self.target_ttft_ms,
            total_uncached_ms=total_uncached_ms,
            target_met=total_uncached_ms <= self.target_ttft_ms,
            stage_timings_ms=stage_timings,
            notes=case.notes,
        )

    def run_cases(
        self,
        cases: tuple[GoldEvalCase, ...],
        *,
        method: RetrievalMethod = RetrievalMethod.HYBRID,
    ) -> LatencyReport:
        results = tuple(self.run_case(case, method=method) for case in cases)
        total_cases = len(results)
        cases_under_target = sum(1 for result in results if result.target_met)
        totals = [result.total_uncached_ms for result in results]

        metrics: dict[str, float | int] = {
            "average_total_uncached_ms": round(sum(totals) / total_cases, 3) if total_cases else 0.0,
            "p50_total_uncached_ms": _percentile(totals, 0.50),
            "p95_total_uncached_ms": _percentile(totals, 0.95),
            "max_total_uncached_ms": round(max(totals), 3) if totals else 0.0,
            "target_met_rate": round(cases_under_target / total_cases, 3) if total_cases else 0.0,
        }
        for stage_key in _REQUIRED_STAGE_KEYS:
            metrics[f"avg_{stage_key}"] = (
                round(sum(result.stage_timings_ms[stage_key] for result in results) / total_cases, 3)
                if total_cases
                else 0.0
            )

        return LatencyReport(
            generated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            total_cases=total_cases,
            cases_under_target=cases_under_target,
            target_ttft_ms=self.target_ttft_ms,
            metrics=metrics,
            cases=results,
            metadata={
                "cache_enabled": self.cache_enabled,
                "benchmark_mode": "uncached_path",
                "retrieval_method": method.value,
            },
        )

    def save_report(self, report: LatencyReport, output_dir: str | Path) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        summary_path = output_dir / f"latency_report_{stamp}.json"
        details_path = output_dir / f"latency_cases_{stamp}.jsonl"
        summary_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        details_path.write_text(
            "".join(f"{case.model_dump_json()}\n" for case in report.cases),
            encoding="utf-8",
        )
        return summary_path


def run_latency_benchmark_from_paths(
    *,
    chunks_path: str | Path,
    gold_path: str | Path,
    output_dir: str | Path,
    limit: int | None = None,
    method: RetrievalMethod = RetrievalMethod.HYBRID,
    target_ttft_ms: float = 1500.0,
    dense_index_path: str | None = None,
    dense_collection_name: str = "dense_chunks",
    synthetic_multiplier: int = 1,
) -> LatencyReport:
    runner = LatencyBenchmarkRunner(
        retrieval_service=RetrievalService.from_jsonl(
            str(chunks_path),
            dense_index_path=dense_index_path,
            dense_collection_name=dense_collection_name,
            synthetic_multiplier=synthetic_multiplier,
        ),
        target_ttft_ms=target_ttft_ms,
        cache_enabled=False,
    )
    cases = load_gold_cases(gold_path)
    if limit is not None:
        cases = cases[:limit]
    report = runner.run_cases(cases, method=method)
    report = report.model_copy(
        update={
            "metadata": {
                **report.metadata,
                "synthetic_multiplier": synthetic_multiplier,
                "synthetic_stress_mode": synthetic_multiplier > 1,
                "effective_chunk_count": len(runner.retrieval_service.chunks),
            }
        }
    )
    runner.save_report(report, output_dir)
    return report
