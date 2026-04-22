"""Case law chunker that preserves section-aware boundaries."""

from __future__ import annotations

from functools import lru_cache

from lxml import etree as ET

from tax_rag.chunking.metadata_builder import build_case_chunk_id, build_chunk_record
from tax_rag.schemas import ChunkRecord, NormalizedDocument

NS = {"rs": "http://www.rechtspraak.nl/schema/rechtspraak-1.0"}


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


def _section_title(section: ET._Element) -> str:
    title = section.find("./rs:title", NS)
    title_text = _element_text(title) if title is not None else ""
    return title_text or section.attrib.get("role") or "section"


def _canonical_section_type(section: ET._Element, title: str) -> str:
    role = (section.attrib.get("role") or "").lower()
    title_lower = title.lower()
    if role == "overwegingen":
        return "reasoning"
    if role == "beslissing":
        return "holding"
    if role == "procesverloop" or any(token in title_lower for token in ("feit", "procesverloop", "geding", "ontstaan", "loop")):
        return "facts"
    if any(token in title_lower for token in ("beoordeling", "overweging", "juridisch kader", "proceskosten", "termijn")):
        return "reasoning"
    return _normalize_whitespace(title_lower or "section")


def _leaf_paragroups(node: ET._Element) -> list[ET._Element]:
    paragroups = node.findall("./rs:paragroup", NS)
    leaves: list[ET._Element] = []
    for group in paragroups:
        nested = _leaf_paragroups(group)
        if nested:
            leaves.extend(nested)
        else:
            leaves.append(group)
    return leaves


def chunk_case_document(document: NormalizedDocument) -> list[ChunkRecord]:
    root = _parse_xml(document.source_path)
    body = root.find("./rs:uitspraak", NS)
    if body is None:
        return [
            build_chunk_record(
                document,
                chunk_id=build_case_chunk_id(document, section_type="document", ordinal="body"),
                text=document.text,
                citation_path=document.citation_path or document.title,
                section_type="document",
                metadata={"chunk_kind": "case_fallback"},
            )
        ]

    chunks: list[ChunkRecord] = []
    for section_index, section in enumerate(body.findall("./rs:section", NS), start=1):
        title = _section_title(section)
        section_type = _canonical_section_type(section, title)
        paragroups = _leaf_paragroups(section)
        if not paragroups:
            section_text = _element_text(section, ignored_tags={"title", "footnote", "footnote-ref"})
            if not section_text:
                continue
            ordinal = str(section_index)
            chunks.append(
                build_chunk_record(
                    document,
                    chunk_id=build_case_chunk_id(document, section_type=section_type, ordinal=ordinal),
                    text=_normalize_whitespace(f"{title}: {section_text}"),
                    citation_path=f"{document.citation_path} > {title}",
                    section_type=section_type,
                    metadata={"chunk_kind": "case_section", "section_title": title},
                )
            )
            continue

        for group in paragroups:
            number = _normalize_whitespace(group.findtext("./rs:nr", namespaces=NS) or str(section_index))
            group_text = _element_text(group, ignored_tags={"nr", "footnote", "footnote-ref"})
            if not group_text:
                continue
            chunks.append(
                build_chunk_record(
                    document,
                    chunk_id=build_case_chunk_id(document, section_type=section_type, ordinal=number),
                    text=_normalize_whitespace(f"{title} {number} {group_text}"),
                    citation_path=f"{document.citation_path} > {title} > {number}",
                    section_type=section_type,
                    metadata={"chunk_kind": "case_paragroup", "section_title": title, "section_number": number},
                )
            )

    return chunks or [
        build_chunk_record(
            document,
            chunk_id=build_case_chunk_id(document, section_type="document", ordinal="body"),
            text=document.text,
            citation_path=document.citation_path or document.title,
            section_type="document",
            metadata={"chunk_kind": "case_fallback"},
        )
    ]
