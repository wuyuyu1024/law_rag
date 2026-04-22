"""Law chunker that preserves article, paragraph, and subparagraph context."""

from __future__ import annotations

from functools import lru_cache

from lxml import etree as ET

from tax_rag.chunking.metadata_builder import build_chunk_record, build_law_chunk_id
from tax_rag.schemas import ChunkRecord, NormalizedDocument


def _local_name(tag: str) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _element_text(element: ET._Element, ignored_tags: set[str] | None = None) -> str:
    ignored_tags = ignored_tags or set()
    parts: list[str] = []

    def visit(node: ET._Element) -> None:
        if _local_name(node.tag) in ignored_tags:
            return
        if node.text and node.text.strip():
            parts.append(node.text)
        for child in node:
            visit(child)
            if child.tail and child.tail.strip():
                parts.append(child.tail)

    visit(element)
    return _normalize_whitespace(" ".join(parts))


@lru_cache(maxsize=32)
def _parse_xml(source_path: str) -> ET._Element:
    return ET.parse(
        source_path,
        parser=ET.XMLParser(remove_blank_text=True, recover=True, huge_tree=True),
    ).getroot()


def _article_node(document: NormalizedDocument) -> ET._Element | None:
    root = _parse_xml(document.source_path)
    for article in root.findall(".//artikel"):
        article_nr = article.findtext("./kop/nr")
        if _normalize_whitespace(article_nr or "") == _normalize_whitespace(document.article or ""):
            return article
    return None


def _build_subparagraph_chunks(
    document: NormalizedDocument,
    *,
    paragraph_number: str,
    intro_text: str,
    list_items: list[ET._Element],
) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    paragraph_prefix = f"Lid {paragraph_number}."
    for item in list_items:
        subparagraph = _normalize_whitespace(item.findtext("./li.nr") or "")
        item_text = _element_text(item, ignored_tags={"meta-data", "li.nr"})
        if not item_text:
            continue
        text_parts = [paragraph_prefix]
        if intro_text:
            text_parts.append(intro_text)
        if subparagraph:
            text_parts.append(f"Onderdeel {subparagraph}")
        text_parts.append(item_text)
        citation = f"{document.citation_path} > Lid {paragraph_number}"
        if subparagraph:
            citation = f"{citation} > Onderdeel {subparagraph}"
        chunks.append(
            build_chunk_record(
                document,
                chunk_id=build_law_chunk_id(document, paragraph=paragraph_number, subparagraph=subparagraph or None),
                text=_normalize_whitespace(" ".join(text_parts)),
                citation_path=citation,
                paragraph=paragraph_number,
                subparagraph=subparagraph or None,
                metadata={"chunk_kind": "law_subparagraph"},
            )
        )
    return chunks


def chunk_law_document(document: NormalizedDocument) -> list[ChunkRecord]:
    article = _article_node(document)
    if article is None:
        return [
            build_chunk_record(
                document,
                chunk_id=build_law_chunk_id(document),
                text=document.text,
                citation_path=document.citation_path or document.title,
                metadata={"chunk_kind": "law_article_fallback"},
            )
        ]

    paragraphs = article.findall("./lid")
    if not paragraphs:
        return [
            build_chunk_record(
                document,
                chunk_id=build_law_chunk_id(document),
                text=document.text,
                citation_path=document.citation_path or document.title,
                metadata={"chunk_kind": "law_article"},
            )
        ]

    chunks: list[ChunkRecord] = []
    for lid in paragraphs:
        paragraph_number = _normalize_whitespace(lid.findtext("./lidnr") or "")
        intro_parts: list[str] = []
        list_items: list[ET._Element] = []
        for child in lid:
            child_name = _local_name(child.tag)
            if child_name in {"meta-data", "lidnr"}:
                continue
            if child_name == "lijst":
                list_items.extend(child.findall("./li"))
                continue
            child_text = _element_text(child, ignored_tags={"meta-data"})
            if child_text:
                intro_parts.append(child_text)

        intro_text = _normalize_whitespace(" ".join(intro_parts))
        if list_items:
            chunks.extend(
                _build_subparagraph_chunks(
                    document,
                    paragraph_number=paragraph_number,
                    intro_text=intro_text,
                    list_items=list_items,
                )
            )
            continue

        if not intro_text:
            continue
        citation = f"{document.citation_path} > Lid {paragraph_number}" if paragraph_number else (document.citation_path or document.title)
        text = _normalize_whitespace(f"Lid {paragraph_number}. {intro_text}" if paragraph_number else intro_text)
        chunks.append(
            build_chunk_record(
                document,
                chunk_id=build_law_chunk_id(document, paragraph=paragraph_number or None),
                text=text,
                citation_path=citation,
                paragraph=paragraph_number or None,
                metadata={"chunk_kind": "law_paragraph"},
            )
        )

    return chunks or [
        build_chunk_record(
            document,
            chunk_id=build_law_chunk_id(document),
            text=document.text,
            citation_path=document.citation_path or document.title,
            metadata={"chunk_kind": "law_article_fallback"},
        )
    ]
