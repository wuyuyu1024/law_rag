from pathlib import Path

from tax_rag.ingestion.parser_laws import parse_law_file
from tax_rag.schemas import SourceType


LAW_PATH = Path("data/raw/laws/wet_inkomstenbelasting_2001.xml")


def test_parse_law_file_extracts_article_documents() -> None:
    documents = parse_law_file(LAW_PATH)

    assert documents
    assert all(document.source_type is SourceType.LEGISLATION for document in documents)
    assert any(document.article == "1.1" for document in documents)


def test_parse_law_file_preserves_title_citation_and_source_path() -> None:
    documents = parse_law_file(LAW_PATH)
    article_1_2 = next(document for document in documents if document.article == "1.2")

    assert article_1_2.title.startswith("Wet inkomstenbelasting 2001 - Artikel 1.2")
    assert article_1_2.citation_path == "Wet inkomstenbelasting 2001 > Artikel 1.2"
    assert "partner" in article_1_2.text.lower()
    assert article_1_2.source_path == str(LAW_PATH)
