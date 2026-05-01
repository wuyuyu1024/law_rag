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
    dense_top_k: int = 100
    final_top_k: int = 10
    fusion_strategy: str = "rrf"
    rrf_k: int = 60
    dense_model: str = "demo-hash-embedding-v1"
    dense_dimensions: int = 256
    exact_identifier_boost: float = 3.0
    qdrant_hnsw_m: int = 32
    qdrant_ef_construct: int = 200
    qdrant_search_ef: int = 128
    qdrant_scalar_quantization: bool = True
    qdrant_scalar_quantile: float = 0.99
    qdrant_quantization_always_ram: bool = True
    qdrant_on_disk_vectors: bool = False


@dataclass(frozen=True)
class RerankingConfig:
    enabled: bool = True
    model: str = "deterministic-legal-reranker-v1"
    input_top_k: int = 50
    output_top_k: int = 10
    concept_overlap_weight: float = 0.32
    lexical_overlap_weight: float = 0.26
    dense_weight: float = 0.16
    lexical_weight: float = 0.12
    rrf_weight: float = 0.08
    legislation_bonus: float = 0.08
    max_source_bonus: float = 0.16
    lexical_normalizer: float = 100.0
    rrf_normalizer: float = 0.03


@dataclass(frozen=True)
class SecurityConfig:
    enforcement_stage: str = "pre_retrieval"
    default_classification: str = "public"
    default_allowed_roles: tuple[str, ...] = ("helpdesk", "inspector", "legal_counsel")
    strict_mode: bool = True


@dataclass(frozen=True)
class CacheConfig:
    enabled: bool = False
    backend: str = "in_memory"
    semantic_similarity_threshold: float = 0.985
    namespace_by_role: bool = True


@dataclass(frozen=True)
class AgentConfig:
    relevant_rrf_score_threshold: float = 0.02
    relevant_dense_score_threshold: float = 0.55
    relevant_lexical_score_threshold: float = 55.0
    relevant_rerank_score_threshold: float = 0.20
    ambiguous_rrf_score_floor: float = 0.01
    ambiguous_dense_score_floor: float = 0.30
    ambiguous_lexical_score_floor: float = 20.0
    ambiguous_rerank_score_floor: float = 0.13
    conflicting_score_margin: float = 0.01
    max_retry_attempts: int = 1
    max_answer_citations: int = 2
    snippet_max_chars: int = 240
    emit_execution_trace: bool = True
    trace_top_results: int = 3


@dataclass(frozen=True)
class PromotionConfig:
    enabled: bool = True
    min_answerable_vs_refused_accuracy: float = 0.55
    min_citation_presence_rate: float = 0.95
    max_unauthorized_retrieval_failures: int = 0
    min_exact_lookup_success: float = 0.35
    min_semantic_retrieval_success: float = 0.70
    min_faithfulness_proxy: float = 0.85
    min_context_precision_proxy: float = 0.70
    max_accuracy_regression: float = 0.05
    max_exact_lookup_regression: float = 0.05
    max_semantic_regression: float = 0.05
    max_context_precision_regression: float = 0.05


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
    trace_output_enabled: bool = True
    promotion: PromotionConfig = field(default_factory=PromotionConfig)


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
