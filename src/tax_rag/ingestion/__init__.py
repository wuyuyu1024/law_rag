"""Ingestion module for tax_rag."""
"""Ingestion and normalization entrypoints."""

from tax_rag.ingestion.parser_cases import iter_case_documents, parse_case_file
from tax_rag.ingestion.parser_laws import iter_law_documents, parse_law_file

__all__ = [
    "iter_case_documents",
    "iter_law_documents",
    "parse_case_file",
    "parse_law_file",
]
