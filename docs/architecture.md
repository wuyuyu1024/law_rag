# Architecture Overview

```mermaid
flowchart TB
    subgraph ingestion["Ingestion & Knowledge Structuring"]
        raw["Raw sources"]
        parse["Normalize documents"]
        chunk["Legal-aware chunks"]
        indexes[(Permission-tagged indexes)]
        raw --> parse --> chunk --> indexes
    end

    subgraph retrieval["Retrieval Strategy"]
        request["User query + scope"]
        rbac["Pre-retrieval RBAC filters"]
        retrieve["Hybrid retrieval"]
        rerank["Reranker backend"]
        request --> rbac --> retrieve --> rerank
    end

    subgraph agent["Agentic RAG & Self-Healing"]
        grade{"Evidence sufficient?"}
        answer["Answer with citations"]
        refuse["Structured refusal"]
        grade -- "relevant" --> answer
        grade -- "ambiguous, missing, outdated, or unauthorized" --> refuse
    end

    subgraph ops["Production Ops, Security & Evaluation"]
        cache[(Semantic cache)]
        eval["Evaluation and promotion gate"]
    end

    indexes --> rbac
    rerank --> grade
    answer --> cache
    cache -.->|role, jurisdiction, version namespace| request
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
