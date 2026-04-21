"""Chunking module for tax_rag."""

from tax_rag.chunking.case_chunker import chunk_case_document
from tax_rag.chunking.legal_chunker import chunk_law_document

__all__ = ["chunk_case_document", "chunk_law_document"]
