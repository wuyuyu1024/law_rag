# ADR 010: TTFT and Scale Strategy for the Uncached Path

## Context

The assignment requires the system to operate over hundreds of thousands of documents and tens of millions of chunks while keeping Time-to-First-Token under 1.5 seconds.

This is an uncached-path requirement first, not a cache-only requirement later. Semantic cache is still useful for repeated FAQ-like queries, but the base retrieval and answer path must already be fast enough without depending on cache hits.

The same assignment also requires:
- strict RBAC before retrieval influence
- exact legal identifier handling
- explainable retrieval and citation grounding

That means the latency target cannot be met by dropping security checks or by replacing legal retrieval with a single opaque semantic lookup.

## Decision

Meet the TTFT target primarily through bounded, filter-first retrieval architecture rather than through cache dependence.

The intended production path is:
- enforce RBAC before lexical or dense scoring
- use hybrid retrieval so exact legal identifiers do not rely on dense search alone
- keep candidate counts explicit and capped at every stage
- use Qdrant filtered ANN search for the dense path
- rerank only a narrow candidate window
- generate from a very small final evidence set

Concrete baseline parameters already recorded in this repository:
- lexical retrieval top-k: `50`
- dense retrieval top-k: `100`
- fusion strategy: `RRF`
- RRF `k`: `60`
- reranker input top-k: `50`
- reranker output top-k: `10`
- final answer context top-k: `10`

Concrete production-oriented Qdrant baseline:
- HNSW `m`: `32` to start, increase to `64` if recall requires it
- HNSW `ef_construct`: `200` to start, increase to `512` if indexing cost is acceptable
- search-time `ef`: `128` for normal traffic, increase to `256` for evaluation or high-precision runs
- payload indexes on `allowed_roles`, `security_classification`, `jurisdiction`, `source_type`, `article`, and `ecli`
- scalar quantization first, then product quantization if memory pressure increases
- on-disk vector storage when RAM becomes the bottleneck

## Latency Budget Assumption

The production target should be defended as a staged latency budget, not as a single undifferentiated number.

Reasonable uncached-path budget:
- request parsing and authorization context assembly: `<= 30 ms`
- lexical retrieval over filtered candidates: `<= 80 ms`
- dense ANN retrieval with metadata filters: `<= 250 ms`
- fusion and result shaping: `<= 20 ms`
- reranking over at most 50 candidates: `<= 250 ms`
- evidence grading and control-flow decision: `<= 50 ms`
- answer construction / first-token generation from a short grounded context: `<= 700 ms`

Total target budget:
- `<= 1.38 s` nominal path

This leaves limited headroom for network and serialization overhead while staying under the assignment target of `1.5 s`.

## Why

- Pre-retrieval RBAC reduces the searchable set before scoring, which helps both security and latency.
- Lexical retrieval handles article numbers and ECLI identifiers cheaply and precisely.
- Dense ANN search is reserved for semantic recall and kept narrow through Qdrant filtering and explicit top-k limits.
- RRF is computationally cheap compared with more fragile score-calibration schemes.
- Reranking is useful, but only when applied to a small candidate set.
- Small final evidence windows keep answer generation fast and easier to ground.

## Alternatives Considered

### Rely on semantic cache to meet the TTFT target

Rejected.

Reason:
- Cache should improve median and repeated-query latency, not rescue a base path that is too slow.
- Cache hit rates are workload-dependent and cannot be the main defense for the assignment's core latency constraint.

### Retrieve broadly, then let a heavy reranker fix precision

Rejected.

Reason:
- It increases latency and cost at the worst possible stage.
- It creates a retrieval path that is harder to bound and harder to defend at 20M+ chunks.

### Dense-only retrieval

Rejected.

Reason:
- Exact legal identifiers such as article numbers and ECLI references need an explicit lexical path.
- Dense-only retrieval is weaker for the domain and would force broader retrieval or heavier reranking.

## Tradeoffs

- Strong pre-filtering can reduce recall if metadata is incomplete.
- Tight top-k bounds can miss edge cases that a broader search might catch.
- Narrow reranking windows trade some quality headroom for predictable latency.

These tradeoffs are acceptable because this system is for tax and legal use. In this domain, abstention is safer than widening the search until latency or security becomes unstable.

## Consequences

- Cache is positioned as an optimization layer, not a prerequisite for baseline performance.
- The system has a concrete interview-ready explanation for how it intends to meet the scale constraint.
- Latency defense now aligns with the repository's other core principles: metadata-first, security-first retrieval, and evidence-gated answering.

## Demo vs Production Note

The current repository documents this production path but does not yet benchmark and prove the `< 1.5 s` TTFT target end to end.

The current dense path uses local in-memory Qdrant for the demo baseline, which is useful for runnable tests and architecture discussion but is not itself evidence of production-scale latency behavior.
