# Architecture Overview

```mermaid
flowchart LR
    raw[Raw sources<br/>laws, cases, policy, e-learning]
    parse[Normalize documents<br/>stable IDs and metadata]
    chunk[Legal-aware chunking<br/>article, paragraph, section]
    indexes[(Indexes<br/>Qdrant dense vectors<br/>lexical/exact lookup)]
    request[User query<br/>role, jurisdiction, as-of date]
    rbac[Pre-retrieval RBAC and scope filters]
    retrieve[Hybrid retrieval<br/>lexical + dense + RRF]
    rerank[Reranker backend<br/>deterministic or cross-encoder]
    grade[Evidence grader<br/>relevant, ambiguous, irrelevant]
    answer[Answer with citations]
    refuse[Structured refusal]
    cache[(Semantic cache<br/>public, relevant, non-exact only)]
    eval[Evaluation and promotion gate]

    raw --> parse --> chunk --> indexes
    request --> rbac --> retrieve --> rerank --> grade
    indexes --> rbac
    grade -->|relevant| answer
    grade -->|ambiguous or irrelevant| refuse
    answer --> cache
    cache -. role/jurisdiction/version namespace .-> request
    answer --> eval
    refuse --> eval
```

The important control points are:

- legal hierarchy is captured before chunking, not reconstructed in a prompt
- authorization happens before lexical scoring, dense scoring, fusion, reranking, caching, or generation
- exact legal identifiers keep a precise lexical path
- semantic questions use dense retrieval plus RRF and reranking
- the answer layer can only answer from evidence graded as relevant
- cache writes are allowed only for public, relevant, non-exact answers
- promotion gates check citation presence, faithfulness proxy, context precision proxy, exact lookup, semantic lookup, and unauthorized retrieval failures
