"""Stable retrieval service entrypoint for later agent and app layers."""

from __future__ import annotations

from dataclasses import dataclass, field

from tax_rag.common import DEFAULT_CONFIG
from tax_rag.indexing import DEFAULT_DENSE_COLLECTION_NAME
from tax_rag.retrieval.common import load_chunk_records
from tax_rag.retrieval.dense import retrieve_dense
from tax_rag.retrieval.hybrid import retrieve_hybrid
from tax_rag.retrieval.lexical import retrieve_lexical
from tax_rag.schemas import ChunkRecord, RetrievalMethod, RetrievalRequest, RetrievalResponse, SourceType


@dataclass
class RetrievalService:
    chunks: list[ChunkRecord] = field(default_factory=list)
    default_method: RetrievalMethod = RetrievalMethod.HYBRID
    dense_index_path: str | None = None
    dense_collection_name: str = DEFAULT_DENSE_COLLECTION_NAME

    @classmethod
    def from_jsonl(
        cls,
        path: str,
        *,
        default_method: RetrievalMethod = RetrievalMethod.HYBRID,
        dense_index_path: str | None = None,
        dense_collection_name: str = DEFAULT_DENSE_COLLECTION_NAME,
    ) -> "RetrievalService":
        return cls(
            chunks=load_chunk_records(path),
            default_method=default_method,
            dense_index_path=dense_index_path,
            dense_collection_name=dense_collection_name,
        )

    def retrieve(
        self,
        query: str,
        role: str,
        top_k: int | None = None,
        *,
        method: RetrievalMethod | None = None,
        source_types: tuple[SourceType, ...] = (),
        jurisdiction: str | None = "NL",
    ) -> RetrievalResponse:
        request = RetrievalRequest(
            query=query,
            role=role,
            top_k=top_k or DEFAULT_CONFIG.retrieval.final_top_k,
            source_types=source_types,
            jurisdiction=jurisdiction,
            metadata={
                "dense_index_path": self.dense_index_path,
                "dense_collection_name": self.dense_collection_name,
            },
        )
        retrieval_method = method or self.default_method

        if retrieval_method is RetrievalMethod.LEXICAL:
            return retrieve_lexical(self.chunks, request)
        if retrieval_method is RetrievalMethod.DENSE:
            return retrieve_dense(self.chunks, request)
        if retrieval_method is RetrievalMethod.HYBRID:
            return retrieve_hybrid(self.chunks, request)
        raise ValueError(f"Unsupported retrieval method: {retrieval_method.value}")
