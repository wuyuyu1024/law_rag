"""Citation resolution helpers for retrieval outputs."""

from __future__ import annotations

from dataclasses import dataclass

from tax_rag.schemas import RetrievalResult, SourceReference, SourceType


@dataclass(frozen=True)
class ResolvedCitation:
    label: str
    source_type: SourceType
    source_path: str
    citation_path: str
    doc_id: str
    chunk_id: str


def _source_label(source: SourceReference) -> str:
    if source.ecli:
        return source.ecli
    return source.citation_path.split(" > ", maxsplit=1)[0]


def resolve_source_reference(source: SourceReference) -> ResolvedCitation:
    label = _source_label(source)
    return ResolvedCitation(
        label=label,
        source_type=source.source_type,
        source_path=source.source_path,
        citation_path=source.citation_path,
        doc_id=source.doc_id,
        chunk_id=source.chunk_id,
    )


def resolve_result_citation(result: RetrievalResult) -> ResolvedCitation:
    return resolve_source_reference(result.source)

