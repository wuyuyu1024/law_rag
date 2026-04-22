import json
from pathlib import Path

from tax_rag.eval import GoldEvalCase, run_latency_benchmark_from_paths
from tax_rag.schemas import AnswerOutcome, ChunkRecord, RetrievalMethod, SecurityClassification, SourceType


def _chunk(
    *,
    chunk_id: str,
    source_type: SourceType,
    text: str,
    citation_path: str,
    allowed_roles: tuple[str, ...],
    security_classification: SecurityClassification,
    article: str | None = None,
) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=chunk_id,
        doc_id=f"doc:{chunk_id}",
        text=text,
        citation_path=citation_path,
        source_type=source_type,
        jurisdiction="NL",
        allowed_roles=allowed_roles,
        source_path=f"fixtures/{chunk_id}.xml",
        article=article,
        security_classification=security_classification,
    )


def _write_gold(path: Path, cases: list[GoldEvalCase]) -> None:
    path.write_text("".join(f"{case.model_dump_json()}\n" for case in cases), encoding="utf-8")


def test_run_latency_benchmark_from_paths_reports_stage_timings_and_saves_artifacts(tmp_path: Path) -> None:
    chunk = _chunk(
        chunk_id="law-home-office",
        source_type=SourceType.LEGISLATION,
        text="Home office expense deductions are limited for mixed private and business use.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 3.16",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="3.16",
    )
    chunks_path = tmp_path / "chunks.jsonl"
    chunks_path.write_text(f"{json.dumps(chunk.to_dict(), ensure_ascii=False)}\n", encoding="utf-8")

    gold_path = tmp_path / "gold.jsonl"
    _write_gold(
        gold_path,
        [
            GoldEvalCase(
                case_id="benchmark_home_office",
                category="semantic_lookup",
                query="deductibility of home office expenses",
                role="helpdesk",
                expected_outcome=AnswerOutcome.ANSWERED,
            )
        ],
    )

    output_dir = tmp_path / "benchmark_runs"
    report = run_latency_benchmark_from_paths(
        chunks_path=chunks_path,
        gold_path=gold_path,
        output_dir=output_dir,
        limit=1,
        method=RetrievalMethod.HYBRID,
        target_ttft_ms=100_000.0,
    )

    assert report.total_cases == 1
    assert report.cases_under_target == 1
    assert report.metadata["cache_enabled"] is False
    assert report.metadata["synthetic_multiplier"] == 1
    assert report.metadata["synthetic_stress_mode"] is False
    case = report.cases[0]
    for stage_key in (
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
    ):
        assert stage_key in case.stage_timings_ms

    assert any(path.suffix == ".json" for path in output_dir.iterdir())
    assert any(path.suffix == ".jsonl" for path in output_dir.iterdir())


def test_run_latency_benchmark_supports_synthetic_stress_multiplier(tmp_path: Path) -> None:
    chunk = _chunk(
        chunk_id="law-home-office",
        source_type=SourceType.LEGISLATION,
        text="Home office expense deductions are limited for mixed private and business use.",
        citation_path="Wet inkomstenbelasting 2001 > Artikel 3.16",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="3.16",
    )
    chunks_path = tmp_path / "chunks.jsonl"
    chunks_path.write_text(f"{json.dumps(chunk.to_dict(), ensure_ascii=False)}\n", encoding="utf-8")

    gold_path = tmp_path / "gold.jsonl"
    _write_gold(
        gold_path,
        [
            GoldEvalCase(
                case_id="benchmark_home_office_stress",
                category="semantic_lookup",
                query="deductibility of home office expenses",
                role="helpdesk",
                expected_outcome=AnswerOutcome.ANSWERED,
            )
        ],
    )

    report = run_latency_benchmark_from_paths(
        chunks_path=chunks_path,
        gold_path=gold_path,
        output_dir=tmp_path / "benchmark_runs",
        limit=1,
        method=RetrievalMethod.HYBRID,
        target_ttft_ms=100_000.0,
        synthetic_multiplier=3,
    )

    assert report.metadata["synthetic_multiplier"] == 3
    assert report.metadata["synthetic_stress_mode"] is True
    assert report.metadata["effective_chunk_count"] == 3
