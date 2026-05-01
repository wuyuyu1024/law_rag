"""Parse Dutch law XML into normalized article-level records."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from lxml import etree as ET

from tax_rag.schemas import NormalizedDocument, SourceType


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


def _article_body(article: ET._Element) -> str:
    parts: list[str] = []
    for child in article:
        child_name = _local_name(child.tag)
        if child_name in {"kop", "meta-data"}:
            continue
        child_text = _element_text(child, ignored_tags={"meta-data"})
        if child_text:
            parts.append(child_text)
    return _normalize_whitespace(" ".join(parts))


def parse_law_file(path: str | Path) -> list[NormalizedDocument]:
    path = Path(path)
    root = ET.parse(
        str(path),
        parser=ET.XMLParser(remove_blank_text=True, recover=True, huge_tree=True),
    ).getroot()
    bwb_id = root.attrib.get("bwb-id", path.stem)
    effective_date = root.attrib.get("inwerkingtreding")
    citeertitel_node = root.find(".//citeertitel")
    intitule_node = root.find(".//intitule")
    citeertitel = _element_text(citeertitel_node, ignored_tags={"meta-data"}) if citeertitel_node is not None else ""
    intitule = _element_text(intitule_node, ignored_tags={"meta-data"}) if intitule_node is not None else ""
    law_title = _normalize_whitespace(citeertitel or intitule or path.stem)

    documents: list[NormalizedDocument] = []
    for article in root.findall(".//artikel"):
        article_nr = article.findtext("./kop/nr")
        article_title = article.findtext("./kop/titel")
        article_label = _normalize_whitespace(article.attrib.get("label", "") or f"Artikel {article_nr or ''}")
        article_text = _article_body(article)
        if not article_text:
            continue

        title = law_title
        if article_title:
            title = f"{law_title} - {article_label}: {_normalize_whitespace(article_title)}"
        citation_path = _normalize_whitespace(f"{law_title} > {article_label}")
        doc_id = f"law:{bwb_id}:{article_nr or article.attrib.get('id', '')}"

        documents.append(
            NormalizedDocument(
                doc_id=doc_id,
                source_type=SourceType.LEGISLATION,
                title=title,
                jurisdiction="NL",
                effective_date=effective_date,
                valid_from=effective_date,
                article=_normalize_whitespace(article_nr) if article_nr else None,
                citation_path=citation_path,
                text=article_text,
                source_path=str(path),
                metadata={
                    "bwb_id": bwb_id,
                    "article_label": article_label,
                    "document_title": law_title,
                    "article_status": article.attrib.get("status"),
                },
            )
        )

    return documents


def iter_law_documents(raw_dir: str | Path) -> Iterator[NormalizedDocument]:
    raw_dir = Path(raw_dir)
    for path in sorted(raw_dir.glob("*.xml")):
        yield from parse_law_file(path)
