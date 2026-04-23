# ADR 011: Promotion Gates and Structured Execution Traces

## Context

The assignment requires pre-deployment evaluation before new embedding, reranking, or generation changes are promoted. It also requires enough observability to inspect retrieval behavior, evidence grading, retries, refusals, and citation use.

The repository already had a deterministic evaluation runner, but it did not yet turn that report into an explicit promotion decision and it did not save a dedicated structured trace artifact for debugging regressions.

## Decision

Add two explicit pieces:

- a promotion gate driven by the evaluation report
- structured execution traces attached to agent responses and exported during eval runs

The promotion gate now checks:
- absolute thresholds for answer/refusal accuracy, citation presence, unauthorized retrieval failures, exact lookup success, semantic retrieval success, faithfulness proxy, and context precision proxy
- optional non-regression tolerances against a prior approved eval report

The execution trace now records:
- query understanding and transformation
- retrieval completions with authorized/denied counts, timings, and top result summaries
- evidence grading decisions
- retry scheduling
- final answer/refusal outcome and cited paths

## Why

- A saved eval report is useful, but a pass/fail promotion decision is what a CI or release process actually needs.
- Structured traces make retrieval and refusal regressions inspectable without relying on ad hoc print debugging.
- Both features fit the repository's existing priorities: explicit control flow, explicit thresholds, and inspectable outputs.

## Alternatives Considered

### Rely on manual reading of eval reports before rollout

Rejected.

Reason:
- That is too informal for a system meant to defend legal and tax accuracy.
- It does not create a consistent promotion rule for CI or local release checks.

### Add a full tracing stack immediately

Rejected for now.

Reason:
- The demo does not need a full observability backend yet.
- JSONL trace artifacts are enough to make retries, refusals, and retrieval decisions inspectable in a local baseline.

## Tradeoffs

- The current promotion thresholds are concrete but still baseline-oriented rather than final production SLOs.
- The trace payload is intentionally compact and does not yet include every internal intermediate.
- The benefit is a runnable, testable, auditable promotion and debugging path without introducing a heavy telemetry dependency.

## Consequences

- Model or retrieval changes now have a concrete local gating command.
- Eval runs now emit trace artifacts that support regression debugging and demo inspection.
- The repository can describe a credible CI promotion story even before adding a fuller observability backend.
