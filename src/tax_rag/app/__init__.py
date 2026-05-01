"""App-facing module for tax_rag."""

from tax_rag.app.cache import CachedCorrectiveRAGAgent, semantic_cache_from_config
from tax_rag.app.cli import format_agent_response, run_demo_query

__all__ = ["CachedCorrectiveRAGAgent", "format_agent_response", "run_demo_query", "semantic_cache_from_config"]
