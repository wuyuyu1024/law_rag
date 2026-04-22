# ADR 005: Qdrant for Dense Retrieval, Hybrid Search with RRF

## Context

Queries in this system mix exact legal identifiers and semantic intent:
- `ECLI:NL:HR:2025:99`
- `Artikel 3.114 lid 2`
- natural-language tax questions such as home-office deductibility

The assignment also requires concrete vector database choices and explicit retrieval parameters.

## Decision

- Use Qdrant as the vector database choice for the architecture.
- Keep lexical retrieval separate and explicit in application code.
- Combine lexical and dense retrieval with Reciprocal Rank Fusion (RRF).

## Why

### Why Qdrant

- Qdrant's point-plus-payload model maps directly to chunk-level legal retrieval.
- The payload model aligns with metadata-first authorization and filtering.
- Qdrant exposes concrete HNSW and quantization settings that are easy to specify and defend.
- It fits a Python-first demo and still maps cleanly to a production deployment path.

### Why hybrid retrieval

- Dense retrieval is good for semantic recall.
- Lexical retrieval is critical for exact identifiers like article numbers and ECLI references.
- Legal search is not safely handled by dense-only retrieval.

### Why RRF

- RRF is simple, robust, and easy to inspect.
- It avoids fragile direct score calibration between lexical and dense retrievers.
- It is a strong baseline for a legal domain where exact lookups and semantic concepts must coexist.

## Alternatives Considered

### Weaviate

Accepted as a credible alternative, but not selected.

Reason:
- Weaviate supports pre-filtered vector search, HNSW tuning, quantization, and built-in RBAC.
- Qdrant was preferred because its payload-centric model maps more directly to chunk-level authorization and keeps the retrieval control plane more explicit.

### Dense-only retrieval

Rejected.

Reason:
- It underperforms on exact legal identifiers.

### Weighted score blending

Rejected as the initial baseline.

Reason:
- It requires more score calibration and is less transparent than RRF for an early legal-retrieval baseline.

## Tradeoffs

- Hybrid retrieval is more complex than a single retriever.
- Qdrant adds operational infrastructure compared with a pure in-process demo.
- The benefit is much stronger alignment with the assignment's scale, filtering, and explainability requirements.

## Consequences

- The system can handle exact identifiers and semantic intent in one retrieval API.
- Retrieval decisions remain inspectable at each stage.
- The architecture is easier to defend because the vector DB choice and retrieval fusion are both tied to concrete legal-search constraints.
