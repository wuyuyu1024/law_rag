# ADR 014: Configurable Reranker Backend Boundary

## Context

The assignment expects a production-quality retrieval stack with a learned reranker, but the demo must stay reproducible on a local machine without forcing a heavyweight model download. ADR 009 introduced the deterministic reranker to stabilize the evaluation baseline. The next step was to make that baseline replaceable without weakening the security and evaluation guarantees already in place.

## Decision

Reranking now has a backend boundary:

- `deterministic` remains the default backend for local tests, CI, and repeatable interviews
- `cross_encoder` is an optional adapter for a `sentence-transformers` cross-encoder model
- the configured production-shaped model is `BAAI/bge-reranker-v2-m3`
- hybrid retrieval selects the backend through config and records `reranker_backend` and `reranker_model` in response metadata

The cross-encoder adapter lazy-loads the model only when selected. The package is not a required dependency for the deterministic baseline.

## Alternatives Considered

### Replace the deterministic reranker immediately

That would align more closely with the production target, but it would make local verification slower and less reliable. It would also introduce network/model-cache requirements into tests that currently run deterministically.

### Keep only the deterministic reranker

That was simple, but it left the implementation looking like a dead-end heuristic. The assignment is stronger if the demo proves the control-flow boundary where a real reranker is plugged in.

## Tradeoffs

Accepted:

- one more abstraction in the retrieval module
- optional runtime behavior that needs clear documentation
- the default backend is still not the production-final relevance model

Gained:

- deterministic local verification remains fast
- learned reranking can be enabled without rewriting hybrid retrieval
- retrieval traces identify which reranker made the ranking decision
- RBAC still happens before retrieval, fusion, and reranking regardless of backend

## Consequences

The repo can now explain both sides honestly: it has a stable deterministic baseline for the submitted demo and a concrete production path for replacing that baseline with a multilingual cross-encoder served internally.
