#!/usr/bin/env python3
"""Run curated interview demo questions against the local RAG pipeline."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from tax_rag.agent import CorrectiveRAGAgent
from tax_rag.app.cache import CachedCorrectiveRAGAgent
from tax_rag.app.cli import format_agent_response
from tax_rag.cache import InMemorySemanticCache
from tax_rag.retrieval import RetrievalMethod, RetrievalService
from tax_rag.schemas import AgentResponse


@dataclass(frozen=True)
class DemoCase:
    label: str
    query: str
    role: str = "helpdesk"
    method: RetrievalMethod = RetrievalMethod.HYBRID


DEMO_CASES: tuple[DemoCase, ...] = (
    DemoCase(
        label="Exact statutory citation",
        query="Artikel 1:1 lid 1 onderdeel a",
        method=RetrievalMethod.LEXICAL,
    ),
    DemoCase(
        label="Semantic 30 percent ruling question",
        query="how does 30% ruling work if the employee change jobs to another employer",
    ),
    DemoCase(
        label="Cache hit for repeated public semantic answer",
        query="how does 30% ruling work if the employee change jobs to another employer",
    ),
    DemoCase(
        label="Unauthorized restricted-source refusal",
        query="fraud signal triage playbook",
    ),
    DemoCase(
        label="Authorized restricted-source answer",
        query="fraud signal triage playbook",
        role="inspector",
    ),
    DemoCase(
        label="Outdated as-of-date refusal",
        query="Artikel 1:1 lid 1 onderdeel a as of 2024-01-01",
    ),
)


def _summary(response: AgentResponse) -> str:
    citations = (
        "; ".join(citation.citation_path for citation in response.citations)
        if response.outcome.value == "answered"
        else "not used for refused response"
    )
    cache = response.metadata.get("semantic_cache")
    cache_summary = ""
    if isinstance(cache, dict):
        cache_summary = f", cache_hit={cache.get('hit')}, cache_stored={cache.get('stored')}"
    return (
        f"outcome={response.outcome.value}, grade={response.evidence.grade.value}, "
        f"reason={response.evidence.refusal_reason.value if response.evidence.refusal_reason else 'none'}"
        f"{cache_summary}, citations={citations}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run curated law_rag interview demo questions.")
    parser.add_argument(
        "--chunks-path", default="data/chunks/legal_chunks.jsonl", help="Chunk JSONL used for retrieval"
    )
    parser.add_argument("--dense-index-path", default=None, help="Optional persistent local Qdrant index directory")
    parser.add_argument("--dense-collection-name", default="dense_chunks", help="Persistent Qdrant collection name")
    parser.add_argument("--details", action="store_true", help="Print full response details for every case")
    args = parser.parse_args()

    retrieval_service = RetrievalService.from_jsonl(
        args.chunks_path,
        dense_index_path=args.dense_index_path,
        dense_collection_name=args.dense_collection_name,
    )
    agent = CachedCorrectiveRAGAgent(
        agent=CorrectiveRAGAgent(retrieval_service=retrieval_service),
        cache=InMemorySemanticCache(),
        cache_backend_name="in_memory",
    )

    for index, case in enumerate(DEMO_CASES, start=1):
        response = agent.answer(case.query, case.role, method=case.method)
        print(f"\n[{index}] {case.label}")
        print(f"role={case.role}")
        print(f"query={case.query}")
        print(_summary(response))
        if args.details:
            print()
            print(format_agent_response(response))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
