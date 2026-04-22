"""Baseline configuration models for the Phase 0 scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LawChunkingConfig:
    target_unit: str = "article_paragraph"
    fallback_target_chars: int = 1400
    overlap_chars: int = 120
    preserve_citation_path: bool = True


@dataclass(frozen=True)
class CaseChunkingConfig:
    preferred_sections: tuple[str, ...] = ("facts", "reasoning", "holding")
    fallback_target_chars: int = 1500
    overlap_chars: int = 120
    preserve_ecli: bool = True


@dataclass(frozen=True)
class ChunkingConfig:
    law: LawChunkingConfig = field(default_factory=LawChunkingConfig)
    case_law: CaseChunkingConfig = field(default_factory=CaseChunkingConfig)


@dataclass(frozen=True)
class RetrievalConfig:
    vector_store: str = "qdrant"
    lexical_top_k: int = 50
    dense_top_k: int = 50
    final_top_k: int = 10
    fusion_strategy: str = "rrf"
    rrf_k: int = 60
    dense_model: str = "demo-hash-embedding-v1"
    dense_dimensions: int = 256
    exact_identifier_boost: float = 3.0


@dataclass(frozen=True)
class RerankingConfig:
    enabled: bool = False
    model: str = "placeholder"
    input_top_k: int = 20
    output_top_k: int = 5


@dataclass(frozen=True)
class SecurityConfig:
    enforcement_stage: str = "pre_retrieval"
    default_classification: str = "public"
    default_allowed_roles: tuple[str, ...] = ("helpdesk", "inspector", "legal_counsel")
    strict_mode: bool = True


@dataclass(frozen=True)
class CacheConfig:
    enabled: bool = False
    backend: str = "placeholder"
    semantic_similarity_threshold: float = 0.96
    namespace_by_role: bool = True


@dataclass(frozen=True)
class AgentConfig:
    relevant_rrf_score_threshold: float = 0.02
    relevant_dense_score_threshold: float = 0.55
    relevant_lexical_score_threshold: float = 55.0
    ambiguous_rrf_score_floor: float = 0.01
    ambiguous_dense_score_floor: float = 0.30
    ambiguous_lexical_score_floor: float = 20.0
    conflicting_score_margin: float = 0.01
    max_answer_citations: int = 2
    snippet_max_chars: int = 240


@dataclass(frozen=True)
class EvaluationConfig:
    gold_set_path: str = "data/eval/gold_questions.jsonl"
    run_output_dir: str = "data/eval/eval_runs"
    metrics: tuple[str, ...] = (
        "answerable_vs_refused",
        "citation_presence",
        "unauthorized_retrieval_failures",
        "exact_lookup_success",
        "semantic_retrieval_success",
        "faithfulness",
        "context_precision",
    )


@dataclass(frozen=True)
class AppConfig:
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    reranking: RerankingConfig = field(default_factory=RerankingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)


DEFAULT_CONFIG = AppConfig()
