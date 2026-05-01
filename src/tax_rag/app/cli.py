"""Minimal CLI-facing formatting for demo responses."""

from __future__ import annotations

import argparse
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


def _format_execution_trace(events: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for event in events:
        sequence = event.get("sequence")
        name = event.get("event")
        state = event.get("state")
        payload = event.get("payload", {})
        summary_parts = [f"step={sequence}", f"event={name}"]
        if state:
            summary_parts.append(f"state={state}")
        if isinstance(payload, dict):
            if "attempt_label" in payload:
                summary_parts.append(f"attempt={payload['attempt_label']}")
            if "grade" in payload:
                summary_parts.append(f"grade={payload['grade']}")
            if "outcome" in payload:
                summary_parts.append(f"outcome={payload['outcome']}")
            if "focused_query" in payload:
                summary_parts.append(f"focused_query={payload['focused_query']}")
        lines.append("- " + ", ".join(summary_parts))
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

    execution_trace = response.metadata.get("execution_trace")
    if isinstance(execution_trace, (list, tuple)) and execution_trace:
        trace_events = [event for event in execution_trace if isinstance(event, dict)]
        if trace_events:
            lines.extend(["", "execution_trace:"])
            lines.extend(_format_execution_trace(trace_events))

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the minimal tax_rag CLI demo.")
    parser.add_argument("query", help="Question to run through the demo agent")
    parser.add_argument("--chunks-path", default="data/chunks/legal_chunks.jsonl", help="Chunk JSONL used for retrieval")
    parser.add_argument("--role", default="helpdesk", help="Role used for RBAC-constrained retrieval")
    parser.add_argument(
        "--method",
        choices=[member.value for member in RetrievalMethod],
        default=RetrievalMethod.HYBRID.value,
        help="Retrieval method used for the demo query",
    )
    parser.add_argument("--dense-index-path", default=None, help="Optional persistent local Qdrant index directory")
    parser.add_argument("--dense-collection-name", default="dense_chunks", help="Persistent Qdrant collection name")
    args = parser.parse_args()

    response = run_demo_query(
        chunks_path=args.chunks_path,
        query=args.query,
        role=args.role,
        method=RetrievalMethod.from_value(args.method),
        dense_index_path=args.dense_index_path,
        dense_collection_name=args.dense_collection_name,
    )
    print(format_agent_response(response))
    return 0
