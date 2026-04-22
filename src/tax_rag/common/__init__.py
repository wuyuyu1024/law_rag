"""Shared utilities for tax_rag."""
"""Shared utilities and config defaults."""

from tax_rag.common.config import DEFAULT_CONFIG, AppConfig
from tax_rag.common.stress import expand_chunks_for_stress

__all__ = ["AppConfig", "DEFAULT_CONFIG", "expand_chunks_for_stress"]
