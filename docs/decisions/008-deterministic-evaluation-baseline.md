# ADR 008: Deterministic Evaluation Baseline with Gold Questions

## Context

The assignment requires repeatable evaluation before promotion of retrieval or model changes. The repository now has local retrieval, grading, refusal, and control flow, so the next step is to measure them against a small gold set.

## Decision

Add a deterministic evaluation runner with:
- a small JSONL gold set
- explicit expected outcomes and citation expectations
- saved per-case results for inspection
- summary metrics tied back to assignment goals

The initial metrics include:
- answerable vs refused accuracy
- citation presence
- unauthorized retrieval failures
- exact lookup success
- semantic retrieval success
- faithfulness proxy
- context precision proxy

## Why

- The project needs a repeatable regression signal before adding more complex generation or model-backed components.
- A local deterministic runner works without API keys and fits the current baseline architecture.
- The gold set forces the team to make expected system behavior explicit.

## Alternatives Considered

### Waiting for Ragas or DeepEval before adding any evaluation

Rejected.

Reason:
- The repository already needed a regression harness now.
- A simple deterministic evaluation baseline is better than having no evaluation while waiting for full LLM-based scoring.

### Ad hoc notebook-based checks only

Rejected.

Reason:
- They are harder to rerun and compare over time.
- They do not create durable artifacts for regression tracking.

## Tradeoffs

- The current faithfulness and context-precision signals are proxy metrics, not full semantic evaluators.
- The benefit is a local, inspectable, rerunnable evaluation loop that can later be upgraded rather than replaced.

## Consequences

- The repository now has a concrete regression entrypoint.
- Future Ragas/DeepEval integration can reuse the same gold set and reporting workflow.
- The evaluation layer is explicit enough to discuss in interviews, including what is a proxy today and what should become model-based later.
