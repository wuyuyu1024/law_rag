"""Agent control module for tax_rag."""

from tax_rag.agent.baseline import EvidenceGatedAgent, build_agent_response
from tax_rag.agent.evidence import grade_evidence

__all__ = [
    "EvidenceGatedAgent",
    "build_agent_response",
    "grade_evidence",
]
