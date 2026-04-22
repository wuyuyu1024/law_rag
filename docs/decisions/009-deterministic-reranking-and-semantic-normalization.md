# ADR 009: Deterministic Reranking and Semantic Normalization

## Context

After the first evaluation baseline, the main weakness was semantic retrieval rather than RBAC or citation handling. The system could protect restricted content and answer exact lookups reasonably well, but broad legal-tax questions such as 30% ruling employer changes were still not retrieving the right statutory chunks reliably.

The repository also needed to stay fully local and testable without requiring an API key or a heavyweight model download in the default path.

## Decision

I added a deterministic retrieval-improvement layer instead of jumping directly to a learned reranker.

The baseline now has two extra pieces:

1. A shared legal-semantic normalization layer
- expands English and Dutch legal-tax phrasing into shared concept tags
- improves dense retrieval for cross-lingual phrasing like `employer` vs `inhoudingsplichtige`
- keeps the behavior inspectable and reproducible

2. A deterministic reranker on top of hybrid retrieval
- reranks fused candidates using concept overlap, lexical overlap, dense score, and a small legislation prior
- preserves explicit score traces such as `rerank_concept_overlap`, `rerank_lexical_overlap`, and `rerank_score`
- does not bypass pre-retrieval RBAC

I also kept two guardrails explicit:
- exact identifier queries preserve lexical priority inside hybrid retrieval
- broad generic eligibility questions supported only by case law are refused rather than treated as general policy answers

## Alternatives Considered

### Add a model-based cross-encoder reranker immediately

This would likely improve quality further, but it would add model/runtime complexity before the current evaluation baseline was stabilized. It also makes local deterministic testing harder.

### Leave retrieval as dense-plus-RRF only

That was simpler, but the evaluation already showed the semantic baseline was too weak on the 30% ruling and other natural-language retrieval cases.

### Route exact-lookups entirely through lexical retrieval

That fixed some cases but was too blunt because mixed identifier-plus-semantic queries should still benefit from hybrid retrieval. Exact lexical priority inside hybrid was the better compromise.

## Tradeoffs

Accepted:
- more handwritten retrieval logic
- explicit heuristic weights that must be documented and defended
- still not as strong as a real learned reranker

Gained:
- much better semantic retrieval without an API key
- explicit inspectability for interviews and debugging
- stable local tests and repeatable eval runs

## Consequences

- The semantic retrieval baseline is now meaningfully stronger on evaluation.
- The repo still has a clean upgrade path to a real embedding model and cross-encoder reranker later.
- The current reranker should be described honestly as a deterministic baseline, not a production-final relevance model.
