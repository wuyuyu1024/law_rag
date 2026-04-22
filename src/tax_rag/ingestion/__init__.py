"""Ingestion module for tax_rag."""
"""Ingestion and normalization entrypoints."""

from tax_rag.ingestion.parser_cases import iter_case_documents, parse_case_file
from tax_rag.ingestion.parser_laws import iter_law_documents, parse_law_file
from tax_rag.ingestion.synthetic_sources import (
    iter_e_learning_documents,
    iter_policy_documents,
    parse_e_learning_fixture,
    parse_policy_fixture,
)

__all__ = [
    "iter_case_documents",
    "iter_e_learning_documents",
    "iter_law_documents",
    "iter_policy_documents",
    "parse_case_file",
    "parse_e_learning_fixture",
    "parse_law_file",
    "parse_policy_fixture",
]
