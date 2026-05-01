# ADR 013: Redis-Backed Semantic Cache Adapter

## Context

The assignment asks for a semantic cache to reduce repeated-query latency and cost, while preserving strict security and zero-hallucination constraints.

The repository already had a conservative in-memory cache policy. That proved the safety rules locally, but did not yet provide a Redis-backed implementation matching the production recommendation.

## Decision

Add a Redis-backed semantic cache adapter beside the in-memory backend.

Both backends share the same cacheability policy:

- cache only answered responses
- cache only relevant evidence
- reject exact legal identifier queries such as `ECLI`, `Artikel`, `lid`, and `paragraph`
- reject non-public sources
- namespace by role, jurisdiction, corpus version, retrieval version, generator version, and source scope

Redis entries are stored under a hashed namespace key and contain:

- original query
- deterministic semantic vector
- serialized `AgentResponse`
- expiry timestamp

Lookup still computes cosine similarity against cached vectors. It is not an exact string cache.

## Why

- Redis matches the production architecture expected by the assignment without making local tests depend on a running service.
- Keeping in-memory as the default preserves deterministic local evaluation.
- The namespace key prevents answers from crossing role or corpus/model-version boundaries.
- Rejecting exact identifier and restricted-source answers avoids unsafe reuse in legal/tax contexts.

## Tradeoffs

- The adapter stores a small JSON list per namespace key rather than using a vector index inside Redis. This is enough for demo-scale cache semantics and keeps the implementation inspectable.
- Production could replace this with Redis vector search or another ANN-backed cache if FAQ volume grows.
- The current adapter is not wired into the agent request path by default. That is deliberate: the uncached path remains the baseline for evaluation and TTFT budgeting.

## Consequences

- The repo now has a concrete Redis cache implementation for Module 4.
- Docker Compose can be used to run Redis for infrastructure demos.
- Tests continue to use a fake Redis client, so CI remains local and deterministic.
