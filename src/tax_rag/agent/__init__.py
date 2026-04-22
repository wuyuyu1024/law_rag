"""Agent control module for tax_rag."""

from tax_rag.agent.baseline import EvidenceGatedAgent, build_agent_response
from tax_rag.agent.control import CorrectiveRAGAgent
from tax_rag.agent.evidence import grade_evidence
from tax_rag.agent.transform import transform_query

__all__ = [
    "CorrectiveRAGAgent",
    "EvidenceGatedAgent",
    "build_agent_response",
    "grade_evidence",
    "transform_query",
]
