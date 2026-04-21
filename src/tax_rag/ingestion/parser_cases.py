"""Parse Rechtspraak XML case law into normalized case records."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator
from xml.etree import ElementTree as ET

from tax_rag.schemas import NormalizedDocument, SourceType

NS = {
    "dcterms": "http://purl.org/dc/terms/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rs": "http://www.rechtspraak.nl/schema/rechtspraak-1.0",
}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _element_text(element: ET.Element, ignored_tags: set[str] | None = None) -> str:
    ignored_tags = ignored_tags or set()
    parts: list[str] = []

    def visit(node: ET.Element) -> None:
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


def _section_label(section: ET.Element) -> str:
    role = section.attrib.get("role")
    title = section.find("./rs:title", NS)
    title_text = _element_text(title) if title is not None else ""
    if title_text:
        return title_text
    if role:
        return role
    return "section"


def _build_case_text(root: ET.Element) -> str:
    parts: list[str] = []
    summary = root.find("./rs:inhoudsindicatie", NS)
    if summary is not None:
        summary_text = _element_text(summary)
        if summary_text:
            parts.append(f"Inhoudsindicatie: {summary_text}")

    body = root.find("./rs:uitspraak", NS)
    if body is None:
        return _normalize_whitespace(" ".join(parts))

    info = body.find("./rs:uitspraak.info", NS)
    if info is not None:
        info_text = _element_text(info)
        if info_text:
            parts.append(info_text)

    for section in body.findall("./rs:section", NS):
        label = _section_label(section)
        section_text = _element_text(section, ignored_tags={"title", "footnote", "footnote-ref"})
        if section_text:
            parts.append(f"{label}: {section_text}")

    return _normalize_whitespace("\n\n".join(parts))


def parse_case_file(path: str | Path) -> NormalizedDocument:
    path = Path(path)
    root = ET.parse(path).getroot()

    ecli = root.findtext("./rdf:RDF/rdf:Description/dcterms:identifier", namespaces=NS)
    court = root.findtext("./rdf:RDF/rdf:Description/dcterms:creator", namespaces=NS)
    decision_date = root.findtext("./rdf:RDF/rdf:Description/dcterms:date", namespaces=NS)

    title = root.findtext(
        "./rdf:RDF/rdf:Description[@rdf:about]/dcterms:title",
        namespaces=NS,
    )
    normalized_title = _normalize_whitespace(title or f"{ecli or path.stem} {court or ''}")
    text = _build_case_text(root)

    return NormalizedDocument(
        doc_id=f"case:{ecli or path.stem}",
        source_type=SourceType.CASE_LAW,
        title=normalized_title,
        jurisdiction="NL",
        text=text,
        source_path=str(path),
        ecli=_normalize_whitespace(ecli) if ecli else None,
        court=_normalize_whitespace(court) if court else None,
        decision_date=decision_date,
        citation_path=_normalize_whitespace(ecli or path.stem),
        metadata={
            "document_kind": _local_name(root.find("./rs:uitspraak", NS).tag) if root.find("./rs:uitspraak", NS) is not None else None,
            "section_count": len(root.findall("./rs:uitspraak/rs:section", NS)),
        },
    )


def iter_case_documents(raw_dir: str | Path) -> Iterator[NormalizedDocument]:
    raw_dir = Path(raw_dir)
    for path in sorted(raw_dir.glob("*.xml")):
        yield parse_case_file(path)
