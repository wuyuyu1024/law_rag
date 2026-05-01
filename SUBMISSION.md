# Submission Summary

This repository is a demo implementation for the technical assessment in [assignment.md](./assignment.md).

It is intentionally smaller than the full production target, but it is designed to answer the assignment directly:

- what is implemented in the runnable demo
- what is recommended for production
- which exact parameters and controls matter for a tax-authority RAG system

## Scope Clarification

Implemented in demo:

- Dutch legislation and Dutch case law ingestion
- synthetic internal policy and e-learning stand-ins
- legal-aware chunking with citation preservation
- pre-retrieval RBAC
- lexical, dense, and hybrid retrieval
- configurable reranking backend with a deterministic local default
- evidence grading, refusal, bounded retry, and execution traces
- local evaluation runner, promotion gate, and TTFT benchmark harness

Recommended for production:

- full internal corpus coverage, including restricted operational manuals, memos, wiki-style guidance, and historical versions
- production Qdrant deployment with filter-aware ANN tuning, quantization, payload indexes, and persistent storage
- learned multilingual embeddings and learned reranking
- Redis-backed semantic cache with strict safety gates
- deeper observability and richer CI evaluators

## Module 1: Ingestion and Knowledge Structuring

### Chunking strategy

Decision:

- treat legal hierarchy as data, not prompt-only context
- normalize raw sources into canonical document records before chunking
- preserve legal citation path on every chunk

Implemented in demo:

- laws are chunked by article, paragraph (`lid`), and list-item boundaries
- case law is chunked by section-aware boundaries such as `facts`, `reasoning`, and `holding`
- every chunk preserves `chunk_id`, `doc_id`, `citation_path`, `source_type`, `jurisdiction`, `allowed_roles`, and validity metadata when available

Pseudo-code:

```python
for document in normalized_documents:
    if document.source_type == "legislation":
        for article in document.articles:
            for paragraph in article.paragraphs:
                chunk = {
                    "chunk_id": stable_chunk_id(document.doc_id, article.number, paragraph.number),
                    "doc_id": document.doc_id,
                    "text": paragraph.text,
                    "citation_path": f"{document.title} > Artikel {article.number} > Lid {paragraph.number}",
                    "article": article.number,
                    "paragraph": paragraph.number,
                    "jurisdiction": document.jurisdiction,
                    "allowed_roles": document.allowed_roles,
                }
                write_jsonl(chunk)
```

Why:

- generic recursive splitters break legal traceability
- the answer layer must be able to cite a specific article and paragraph, not only a blob of text

### Vector database and scale choice

Decision:

- select Qdrant for the production architecture

Why:

- metadata filtering is a first-class requirement because RBAC must apply before retrieval influence
- Qdrant supports payload filtering, payload indexes, HNSW tuning, quantization, and on-disk vector storage

Concrete production configuration:

- vector DB: `Qdrant`
- distance: `cosine`
- HNSW `m`: `32` to start, increase to `64` if recall requires it
- HNSW `ef_construct`: `200` to start, increase to `512` if indexing cost is acceptable
- search-time `ef`: `128` for normal traffic, `256` for evaluation/high-precision runs
- payload indexes:
  - `allowed_roles`
  - `security_classification`
  - `security_classification_rank`
  - `jurisdiction`
  - `source_type`
  - `valid_from`
  - `valid_to`
  - `article`
  - `ecli`
- memory controls:
  - scalar quantization first
  - product quantization if RAM pressure increases further
  - on-disk vector storage when the corpus grows past RAM-friendly size

Implemented in demo:

- local Qdrant-backed dense retrieval
- persistent local index build/load path
- payload fields already shaped for pre-retrieval security filtering

## Module 2: Retrieval Strategy

### Hybrid retrieval

Decision:

- use hybrid retrieval with lexical retrieval plus dense retrieval
- combine the two with Reciprocal Rank Fusion (`RRF`)

Why:

- legal queries mix exact identifiers and semantic intent
- article numbers and ECLI IDs need a precise lexical path
- semantic retrieval is still necessary for natural-language legal/tax questions
- RRF avoids fragile direct score calibration between lexical and dense scorers

Concrete retrieval parameters:

- lexical top-k: `50`
- dense top-k: `100`
- fusion strategy: `RRF`
- RRF `k`: `60`
- final answer context top-k: `10`

Implemented in demo:

- exact lexical retrieval over legal identifiers
- dense retrieval through Qdrant
- hybrid retrieval with RRF
- exact statutory queries are narrowed to the requested paragraph/subparagraph when that metadata is present

Recommended production dense model:

- multilingual embedding model suitable for Dutch and English legal/tax phrasing
- keep the current demo hashing embedder only as the local deterministic baseline

### Reranking

Decision:

- production path: use a multilingual cross-encoder reranker over a narrow candidate window
- demo path: keep the current deterministic reranker as the default local backend
- implementation boundary: expose reranker backend selection so the production adapter can be enabled without changing hybrid retrieval control flow

Recommended production reranker:

- `BAAI/bge-reranker-v2-m3` served internally

Why this choice:

- multilingual support matters because the assignment mixes Dutch internal sources with English-like user phrasing and legal identifiers
- it supports local deployment for restricted/internal documents, unlike an external API-only path
- it is a better final precision layer than the current handwritten heuristic reranker

Concrete reranking parameters:

- reranker input top-k: `50`
- reranker output top-k: `10`
- rerank only after RBAC filtering and initial retrieval

Implemented in demo:

- deterministic reranker using concept overlap, lexical overlap, dense score, and a small legislation prior
- optional `cross_encoder` reranker adapter that lazy-loads a `sentence-transformers` `CrossEncoder` when that dependency and model are available
- reranker metadata records both backend and model in retrieval traces

## Module 3: Agentic RAG and Self-Healing

### Query transformation

Decision:

- make query transformation inspectable instead of hiding it inside one prompt
- support decomposition and focused retries rather than an opaque one-shot answer path

Implemented in demo:

- explicit transform planning
- bounded corrective retry
- execution traces for transform, retrieval, grading, and final answer/refusal

Recommended production policy:

- decompose multi-part tax questions into subqueries when a question mixes multiple tax concepts, time periods, or document types
- use focused reformulation for failed retrieval attempts
- reserve HyDE-style expansion for broad semantic questions, but disable it for exact identifier lookups

### Corrective RAG control loop

State machine:

1. `understood`
2. `retrieved`
3. `graded`
4. one of:
   - `answered`
   - `retried`
   - `refused`

Retrieval evaluator grades:

- `relevant`
- `ambiguous`
- `irrelevant`

Fallback behavior:

- if `relevant`: answer with citations only from retrieved evidence
- if `ambiguous`: retry once with a focused reformulation; if still ambiguous, refuse
- if `irrelevant`: refuse without generation

Why:

- zero-hallucination tolerance means the system must stop rather than improvise
- inspectable control flow is easier to test and defend than an opaque prompt-only loop

## Module 4: Production Ops, Security, and Evaluation

### Semantic cache

Decision:

- use Redis as a role-aware semantic cache for low-risk FAQ-like queries only

Recommended production cache policy:

- backend: `Redis`
- similarity threshold: `0.985`
- namespace by:
  - `role`
  - `jurisdiction`
  - `source_scope`
  - retrieval/generator version
- store:
  - answer text
  - citations
  - evidence grade
  - retrieval metadata
  - effective-date/version metadata

Do not cache when:

- the query contains exact identifiers such as `ECLI`, article numbers, or paragraph references
- evidence was `ambiguous`
- any restricted/internal source contributed to the answer
- the answer depends on time-sensitive law versioning or unresolved conflicts

Implemented in demo:

- threshold and namespace defaults are documented in config
- an in-memory semantic cache enforces the conservative cacheability policy for local tests and demos
- a Redis-backed semantic cache adapter uses the same conservative policy and role/jurisdiction/version namespace boundaries

### Database-level security

Decision:

- RBAC must be enforced before retrieval scoring, fusion, reranking, caching, or generation

Exact enforcement point:

- apply authorization filters inside the searchable candidate set, not after retrieval
- in the production vector DB, use payload filters on `allowed_roles`, `security_classification`, and other scope fields before ANN scoring
- in the application layer, preserve the same constraint before lexical retrieval

Why:

- retrieve-first/filter-later still allows unauthorized chunks to influence ranking mathematically
- for this assignment, unauthorized content must not affect retrieval, reranking, caching, generation, or evaluation

### CI/CD and observability

Decision:

- treat retrieval, reranking, and generation changes as gated promotions rather than ad hoc updates

Implemented in demo:

- gold evaluation set
- regression runner
- promotion gate
- structured execution traces
- optional exact citation-path and chunk-id gold checks for stricter retrieval precision

Metrics tracked now:

- answerable-vs-refused accuracy
- citation presence rate
- unauthorized retrieval failures
- exact lookup success
- semantic retrieval success
- faithfulness proxy
- context precision proxy
- exact chunk/citation-path match counts where the gold set specifies them

Recommended production extension:

- keep the current deterministic regression set
- add richer faithfulness/context metrics with tools such as `Ragas` or `DeepEval`
- add per-stage latency dashboards and retrieval-quality drift alerts

## Demo Limitations

These limitations are intentional and should be stated plainly to the interviewer:

- the runtime corpus is small and partly simulated
- the current dense embedding and default reranking path are deterministic local baselines, not the final production relevance stack
- the cross-encoder reranker boundary is implemented, but the heavy model dependency is intentionally optional rather than required for local tests
- the repo documents a production TTFT strategy but does not prove `< 1.5 s` at production scale end to end
- the semantic cache has both deterministic in-memory and Redis-backed adapters; wiring cache reads/writes into a production API path would be the next integration step

## Final Position

This repo should be read as:

- a runnable demo that already implements the core security and legal-retrieval behavior
- a concrete architecture specification that a DevOps/AI engineering team can extend toward production
- an intentionally honest submission that separates what is implemented now from what is recommended for a full enterprise rollout
