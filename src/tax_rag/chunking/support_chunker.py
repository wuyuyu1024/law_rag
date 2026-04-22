"""Chunk synthetic internal policy and e-learning documents on section boundaries."""

from __future__ import annotations

from tax_rag.chunking.metadata_builder import build_chunk_record, build_support_chunk_id
from tax_rag.schemas import ChunkRecord, NormalizedDocument, SourceType


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _split_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line[3:].strip()
            current_lines = []
            continue
        if line.startswith("# "):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line[2:].strip()
            current_lines = []
            continue
        current_lines.append(raw_line)

    if current_title is not None:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return [(title, body) for title, body in sections if title]


def _fallback_sections(text: str) -> list[tuple[str, str]]:
    paragraphs = [_normalize_whitespace(part) for part in text.split("\n\n") if part.strip()]
    if not paragraphs:
        return [("Body", _normalize_whitespace(text))]
    return [(f"Paragraph {index}", paragraph) for index, paragraph in enumerate(paragraphs, start=1)]


def chunk_support_document(document: NormalizedDocument) -> list[ChunkRecord]:
    if document.source_type not in {SourceType.INTERNAL_POLICY, SourceType.E_LEARNING}:
        raise ValueError(f"Unsupported source type for support chunking: {document.source_type.value}")

    raw_sections = _split_sections(document.text) or _fallback_sections(document.text)
    chunks: list[ChunkRecord] = []
    chunk_kind = "policy_section" if document.source_type is SourceType.INTERNAL_POLICY else "learning_section"

    for index, (section_title, section_body) in enumerate(raw_sections, start=1):
        text = _normalize_whitespace(f"{section_title}: {section_body}" if section_body else section_title)
        if not text:
            continue
        citation_path = f"{document.citation_path or document.title} > {section_title}"
        chunks.append(
            build_chunk_record(
                document,
                chunk_id=build_support_chunk_id(document, section_label=section_title, ordinal=str(index)),
                text=text,
                citation_path=citation_path,
                metadata={
                    "chunk_kind": chunk_kind,
                    "section_title": section_title,
                },
            )
        )

    return chunks or [
        build_chunk_record(
            document,
            chunk_id=build_support_chunk_id(document, section_label="body", ordinal="1"),
            text=_normalize_whitespace(document.text),
            citation_path=document.citation_path or document.title,
            metadata={"chunk_kind": chunk_kind},
        )
    ]
