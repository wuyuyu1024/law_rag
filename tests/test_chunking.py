import json
from pathlib import Path

from tax_rag.chunking import chunk_case_document, chunk_law_document
from tax_rag.schemas import NormalizedDocument


def _load_document(path: str, needle: str) -> NormalizedDocument:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return NormalizedDocument.from_dict(json.loads(next(line for line in lines if needle in line)))


def test_law_chunker_falls_back_to_article_chunk_when_no_lids() -> None:
    document = _load_document("data/parsed/laws.jsonl", '"doc_id": "law:BWBR0011353:1.1"')

    chunks = chunk_law_document(document)

    assert len(chunks) == 1
    assert chunks[0].chunk_id == "law:BWBR0011353:1.1:body"
    assert chunks[0].citation_path == "Wet inkomstenbelasting 2001 > Artikel 1.1"
    assert chunks[0].doc_id == document.doc_id


def test_law_chunker_preserves_paragraph_and_subparagraph_context() -> None:
    document = _load_document("data/parsed/laws.jsonl", '"doc_id": "law:BWBR0011353:1.2"')

    chunks = chunk_law_document(document)
    target = next(chunk for chunk in chunks if chunk.paragraph == "1" and chunk.subparagraph == "a.")

    assert target.chunk_id == "law:BWBR0011353:1.2:paragraph:1:subparagraph:a"
    assert target.citation_path == "Wet inkomstenbelasting 2001 > Artikel 1.2 > Lid 1 > Onderdeel a."
    assert "partner mede verstaan" in target.text.lower()
    assert target.doc_id == document.doc_id


def test_case_chunker_maps_sections_to_canonical_types() -> None:
    document = _load_document("data/parsed/cases.jsonl", "ECLI:NL:HR:2025:99")

    chunks = chunk_case_document(document)
    section_types = {chunk.section_type for chunk in chunks}

    assert {"facts", "reasoning", "holding"} <= section_types
    assert all(chunk.ecli == document.ecli for chunk in chunks)


def test_case_chunker_preserves_section_citation_paths() -> None:
    document = _load_document("data/parsed/cases.jsonl", "ECLI:NL:GHDHA:2023:2457")

    chunks = chunk_case_document(document)
    facts_chunk = next(chunk for chunk in chunks if chunk.section_type == "facts")

    assert facts_chunk.citation_path.startswith("ECLI:NL:GHDHA:2023:2457 >")
    assert "Procesverloop" in facts_chunk.text or "Feiten" in facts_chunk.text
    assert facts_chunk.doc_id == document.doc_id
