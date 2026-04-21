"""Helpers for deterministic chunk metadata and IDs."""

from __future__ import annotations

import re

from tax_rag.schemas import ChunkRecord, NormalizedDocument

_TOKEN_PATTERN = re.compile(r"[^a-z0-9]+")


def _slug(value: str) -> str:
    return _TOKEN_PATTERN.sub("_", value.lower()).strip("_") or "item"


def build_law_chunk_id(
    document: NormalizedDocument,
    *,
    paragraph: str | None = None,
    subparagraph: str | None = None,
) -> str:
    parts = [document.doc_id]
    if paragraph is not None:
        parts.extend(["paragraph", _slug(paragraph)])
    if subparagraph is not None:
        parts.extend(["subparagraph", _slug(subparagraph)])
    if paragraph is None and subparagraph is None:
        parts.append("body")
    return ":".join(parts)


def build_case_chunk_id(
    document: NormalizedDocument,
    *,
    section_type: str,
    ordinal: str,
) -> str:
    return ":".join([document.doc_id, "section", _slug(section_type), _slug(ordinal)])


def build_chunk_record(
    document: NormalizedDocument,
    *,
    chunk_id: str,
    text: str,
    citation_path: str,
    paragraph: str | None = None,
    subparagraph: str | None = None,
    section_type: str | None = None,
    metadata: dict[str, object] | None = None,
) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=chunk_id,
        doc_id=document.doc_id,
        text=text,
        citation_path=citation_path,
        source_type=document.source_type,
        jurisdiction=document.jurisdiction,
        allowed_roles=document.allowed_roles,
        source_path=document.source_path,
        article=document.article,
        paragraph=paragraph,
        subparagraph=subparagraph,
        ecli=document.ecli,
        court=document.court,
        decision_date=document.decision_date,
        section_type=section_type,
        security_classification=document.security_classification,
        metadata=metadata or {},
    )
