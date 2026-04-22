"""Minimal CLI-facing formatting for demo responses."""

from __future__ import annotations

from typing import Any

from tax_rag.agent import CorrectiveRAGAgent
from tax_rag.retrieval import RetrievalService
from tax_rag.schemas import AgentResponse, RetrievalMethod


def _format_timings(timings: dict[str, Any]) -> list[str]:
    ordered_keys = (
        "request_scoping_ms",
        "security_filter_ms",
        "lexical_retrieval_ms",
        "dense_retrieval_ms",
        "fusion_ms",
        "reranking_ms",
        "retrieval_total_ms",
    )
    lines: list[str] = []
    for key in ordered_keys:
        value = timings.get(key)
        if isinstance(value, int | float):
            lines.append(f"- {key}: {float(value):.3f} ms")
    return lines


def format_agent_response(response: AgentResponse) -> str:
    lines = [
        f"outcome: {response.outcome.value}",
        f"retrieval_method: {response.retrieval_method.value}",
        f"evidence_grade: {response.evidence.grade.value}",
    ]
    if response.evidence.refusal_reason is not None:
        lines.append(f"refusal_reason: {response.evidence.refusal_reason.value}")

    answer_or_explanation = response.answer_text or response.evidence.explanation
    lines.extend(
        [
            "",
            "response:",
            answer_or_explanation,
        ]
    )

    if response.citations:
        lines.extend(["", "citations:"])
        for citation in response.citations:
            lines.append(f"- {citation.citation_path}")

    if response.state_trace:
        lines.extend(["", "state_trace:", " -> ".join(response.state_trace)])

    transform_plan = response.metadata.get("transform_plan")
    if isinstance(transform_plan, dict):
        strategy = transform_plan.get("strategy")
        transformed_queries = transform_plan.get("transformed_queries")
        lines.extend(["", "transform:"])
        lines.append(f"- strategy: {strategy}")
        if transformed_queries:
            lines.append(f"- transformed_queries: {', '.join(transformed_queries)}")

    retrieval_metadata = response.metadata.get("retrieval_metadata")
    if isinstance(retrieval_metadata, dict):
        lines.extend(["", "retrieval:"])
        lines.append(f"- authorized_candidate_count: {retrieval_metadata.get('authorized_candidate_count', 0)}")
        lines.append(f"- denied_count: {retrieval_metadata.get('denied_count', 0)}")
        lines.append(f"- total_chunk_count: {retrieval_metadata.get('total_chunk_count', 0)}")
        timings = retrieval_metadata.get("timings_ms")
        if isinstance(timings, dict):
            lines.append("- timings_ms:")
            lines.extend(_format_timings(timings))

    if "subqueries" in response.metadata:
        subqueries = response.metadata.get("subqueries")
        if isinstance(subqueries, list) and subqueries:
            lines.extend(["", "subqueries:"])
            for item in subqueries:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    "- "
                    + ", ".join(
                        [
                            f"query={item.get('query')}",
                            f"retrieval_method={item.get('retrieval_method')}",
                            f"evidence_grade={item.get('evidence_grade')}",
                        ]
                    )
                )

    return "\n".join(lines)


def run_demo_query(
    *,
    chunks_path: str,
    query: str,
    role: str,
    method: RetrievalMethod = RetrievalMethod.HYBRID,
    dense_index_path: str | None = None,
    dense_collection_name: str = "dense_chunks",
) -> AgentResponse:
    retrieval_service = RetrievalService.from_jsonl(
        chunks_path,
        dense_index_path=dense_index_path,
        dense_collection_name=dense_collection_name,
    )
    agent = CorrectiveRAGAgent(retrieval_service=retrieval_service)
    return agent.answer(query, role, method=method)
