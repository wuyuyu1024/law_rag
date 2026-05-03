# Production Delta

This repository is a runnable architecture demo. The table below separates what is already represented from what remains before a real national tax-authority deployment.

## High-Priority Production Work

| Area | Demo State | Production Delta |
| --- | --- | --- |
| Corpus | Dutch laws, case law, and synthetic internal/e-learning stand-ins | Ingest the full internal corpus: operational manuals, memos, wiki/e-learning modules, historical law versions, and restricted FIOD-style sources |
| Embeddings | Deterministic local hash-style embedding baseline | Serve a multilingual legal/tax embedding model with versioned model registry, drift checks, and offline backfills |
| Reranking | Deterministic default plus optional cross-encoder adapter | Serve `BAAI/bge-reranker-v2-m3` or equivalent internally, benchmark latency, and gate rollout with eval regression tests |
| Vector DB | Local persistent Qdrant path with payload indexes | Run managed/self-hosted Qdrant cluster with replication, backups, payload-index monitoring, HNSW tuning, quantization, and capacity planning |
| Lexical retrieval | In-process exact/lexical retrieval for the demo | Add production BM25/OpenSearch-style service or Qdrant sparse vectors with the same pre-retrieval authorization filters |
| Security | Pre-retrieval RBAC in application and retrieval contracts | Integrate SSO/OIDC, policy engine, row-level/source-level authorization, audit trails, and break-glass procedures |
| Caching | In-memory and Redis semantic cache backends with conservative policy | Deploy Redis with persistence/HA, namespace by corpus/model/security versions, monitor unsafe cache attempts, and add cache invalidation on law/policy updates |
| Generation | Deterministic evidence-based answer construction | Use an approved internal LLM with citation-constrained prompting, structured output validation, and refusal enforcement |
| Observability | Structured traces and eval artifacts | Add dashboards for retrieval latency, TTFT, cache hit rate, refusal rate, authorization denials, citation failures, and model drift |
| Evaluation | Small deterministic gold set and promotion gate | Expand gold set by tax domain, role, language, time period, and document type; add Ragas/DeepEval-style faithfulness and context precision evaluators |
| Operations | Local scripts and Docker Compose services | CI/CD pipelines, blue-green index deployment, rollback, incident runbooks, SLOs, and scheduled re-indexing |

## Scale And Latency Plan

The assignment target is low TTFT despite tens of millions of chunks. The production path should use a latency budget like:

Current demo evidence: the local uncached benchmark over 6,294 chunks is below the assignment target, with p95 TTFT at 728.637 ms. This validates the runnable control flow and timing instrumentation, but it is not a substitute for a production-scale 20M+ chunk load test.

| Stage | Target |
| --- | --- |
| Auth/scope resolution | 20-50 ms |
| Lexical/exact retrieval | 50-120 ms |
| Dense ANN search | 100-250 ms |
| Fusion and filtering | 10-30 ms |
| Reranker on top 50 | 150-400 ms, depending on serving hardware |
| Evidence grading and prompt assembly | 30-80 ms |
| First generated token | remaining budget to stay under 1.5 s |

Controls:

- keep reranker input capped at `50`
- use Qdrant payload indexes for `allowed_roles`, `security_classification`, `jurisdiction`, `source_type`, `valid_from`, `valid_to`, `article`, and `ecli`
- use scalar quantization first and on-disk vectors when the corpus exceeds RAM-friendly size
- use lower `ef` for normal traffic and higher `ef` for high-precision/evaluation runs
- route exact identifier queries through lexical/exact paths before semantic expansion
- use semantic cache only for public, relevant, non-exact answers
- fail closed with refusal if evidence is weak, conflicting, unauthorized, or outdated

## Audit Logging Design

Production should write an audit event for every query and answer/refusal:

- request ID and timestamp
- user ID, role, jurisdiction, and source scope
- query hash plus optionally redacted query text
- retrieval method, model versions, reranker backend, cache hit/miss
- retrieved chunk IDs and citation paths
- authorization denial counts, not denied document text
- evidence grade and refusal reason
- final outcome
- latency timings by stage

Do not log full restricted document text in general application logs. Restricted source snippets should only appear in controlled, access-restricted audit stores when policy permits it.

## Deployment Readiness Bar

Before production rollout:

- all indexed chunks have complete security metadata
- unauthorized retrieval failures remain zero in CI gates
- all answer claims have exact citations
- time-versioned law retrieval is covered in evaluation
- cache invalidation is tested for corpus/model updates
- SSO/OIDC and audit logging pass security review
- load tests demonstrate the TTFT SLO against production-scale indexes
- rollback is tested for embedding, reranker, index, and generator changes
