"""Optional FastAPI application for local demos."""

from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI
from pydantic import BaseModel, Field

from tax_rag.agent import CorrectiveRAGAgent
from tax_rag.retrieval import RetrievalMethod, RetrievalService
from tax_rag.schemas import AgentResponse


class QueryRequest(BaseModel):
    query: str
    role: str = "helpdesk"
    method: RetrievalMethod = RetrievalMethod.HYBRID
    chunks_path: str = "data/chunks/legal_chunks.jsonl"
    top_k: int | None = Field(default=None, gt=0)
    jurisdiction: str | None = "NL"
    dense_index_path: str | None = None
    dense_collection_name: str = "dense_chunks"


app = FastAPI(title="Tax RAG Demo", version="0.1.0")


@lru_cache(maxsize=8)
def _retrieval_service(
    chunks_path: str,
    dense_index_path: str | None,
    dense_collection_name: str,
) -> RetrievalService:
    return RetrievalService.from_jsonl(
        chunks_path,
        dense_index_path=dense_index_path,
        dense_collection_name=dense_collection_name,
    )


def run_query(request: QueryRequest) -> AgentResponse:
    service = _retrieval_service(
        request.chunks_path,
        request.dense_index_path,
        request.dense_collection_name,
    )
    agent = CorrectiveRAGAgent(retrieval_service=service)
    return agent.answer(
        request.query,
        request.role,
        top_k=request.top_k,
        method=request.method,
        jurisdiction=request.jurisdiction,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/query", response_model=AgentResponse)
def query(request: QueryRequest) -> AgentResponse:
    return run_query(request)
