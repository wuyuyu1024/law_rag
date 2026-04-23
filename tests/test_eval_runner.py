import json
from pathlib import Path

from tax_rag.eval import EvalRunner, EvalReport, GoldEvalCase, evaluate_promotion, load_gold_cases
from tax_rag.retrieval import RetrievalMethod, RetrievalService
from tax_rag.schemas import AnswerOutcome, ChunkRecord, SecurityClassification, SourceType


def _chunk(
    *,
    chunk_id: str,
    source_type: SourceType,
    text: str,
    citation_path: str,
    allowed_roles: tuple[str, ...],
    security_classification: SecurityClassification,
    article: str | None = None,
    ecli: str | None = None,
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
        ecli=ecli,
        security_classification=security_classification,
    )


def _write_gold(path: Path, cases: list[GoldEvalCase]) -> None:
    path.write_text("".join(f"{case.model_dump_json()}\n" for case in cases), encoding="utf-8")


def test_load_gold_cases_and_run_eval(tmp_path: Path) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    chunk = _chunk(
        chunk_id="law-1-1",
        source_type=SourceType.LEGISLATION,
        text="Lid 1. Onder bestuursorgaan wordt verstaan: Onderdeel a. een orgaan van een rechtspersoon.",
        citation_path="Algemene wet bestuursrecht > Artikel 1:1 > Lid 1 > Onderdeel a.",
        allowed_roles=("helpdesk", "inspector", "legal_counsel"),
        security_classification=SecurityClassification.PUBLIC,
        article="1:1",
    )
    chunks_path.write_text(f"{json.dumps(chunk.to_dict(), ensure_ascii=False)}\n", encoding="utf-8")

    gold_path = tmp_path / "gold.jsonl"
    _write_gold(
        gold_path,
        [
            GoldEvalCase(
                case_id="exact_awb",
                category="exact_lookup",
                query="Artikel 1:1 lid 1 onderdeel a",
                role="helpdesk",
                expected_outcome=AnswerOutcome.ANSWERED,
                expected_citation_substrings=("Algemene wet bestuursrecht > Artikel 1:1",),
            )
        ],
    )

    cases = load_gold_cases(gold_path)
    runner = EvalRunner(RetrievalService.from_jsonl(str(chunks_path), default_method=RetrievalMethod.LEXICAL))
    report = runner.run_cases(cases)

    assert report.total_cases == 1
    assert report.passed_cases == 1
    assert report.metrics["exact_lookup_success"] == 1.0
    assert report.cases[0].execution_trace[-1]["event"] == "response_finalized"


def test_eval_runner_tracks_unauthorized_retrieval_failures_and_saves_report(tmp_path: Path) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    restricted = _chunk(
        chunk_id="restricted-playbook",
        source_type=SourceType.INTERNAL_POLICY,
        text="Restricted fraud guidance.",
        citation_path="Fraud Signal Triage Playbook > Scope",
        allowed_roles=("inspector", "legal_counsel"),
        security_classification=SecurityClassification.RESTRICTED,
    )
    chunks_path.write_text(f"{json.dumps(restricted.to_dict(), ensure_ascii=False)}\n", encoding="utf-8")

    gold_path = tmp_path / "gold.jsonl"
    _write_gold(
        gold_path,
        [
            GoldEvalCase(
                case_id="unauthorized_playbook",
                category="unauthorized_role",
                query="fraud signal triage playbook",
                role="helpdesk",
                expected_outcome=AnswerOutcome.REFUSED,
                forbidden_citation_substrings=("Fraud Signal Triage Playbook",),
            )
        ],
    )

    runner = EvalRunner(RetrievalService.from_jsonl(str(chunks_path), default_method=RetrievalMethod.DENSE))
    report = runner.run_cases(load_gold_cases(gold_path))
    output_dir = tmp_path / "runs"
    summary_path = runner.save_report(report, output_dir)

    assert report.metrics["unauthorized_retrieval_failures"] == 0
    assert summary_path.exists()
    output_files = list(output_dir.iterdir())
    assert any(path.suffix == ".jsonl" for path in output_files)
    assert any(path.name.startswith("eval_traces_") for path in output_files)


def test_evaluate_promotion_compares_candidate_against_thresholds_and_baseline() -> None:
    baseline_report = EvalReport(
        generated_at="2026-04-23T00:00:00Z",
        total_cases=10,
        passed_cases=8,
        metrics={
            "answerable_vs_refused_accuracy": 0.8,
            "citation_presence_rate": 1.0,
            "unauthorized_retrieval_failures": 0,
            "exact_lookup_success": 0.8,
            "semantic_retrieval_success": 0.8,
            "faithfulness_proxy": 0.9,
            "context_precision_proxy": 0.85,
        },
        cases=(),
        metadata={},
    )
    candidate_report = baseline_report.model_copy(
        update={
            "generated_at": "2026-04-23T01:00:00Z",
            "metrics": {
                **baseline_report.metrics,
                "answerable_vs_refused_accuracy": 0.76,
                "exact_lookup_success": 0.76,
                "semantic_retrieval_success": 0.76,
                "context_precision_proxy": 0.81,
            },
        }
    )

    decision = evaluate_promotion(candidate_report, baseline_report=baseline_report, candidate_label="test-candidate")

    assert decision.candidate_label == "test-candidate"
    assert decision.passed
    assert any(check.name == "exact_lookup_success_vs_baseline" for check in decision.checks)
