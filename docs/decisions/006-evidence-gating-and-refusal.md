# ADR 006: Evidence Gating and Refusal Before Free-Form Generation

## Context

The assignment requires zero-hallucination behavior, explicit citations, and refusal when evidence is missing, ambiguous, conflicting, outdated, or unauthorized.

## Decision

Introduce a deterministic evidence grader before free-form generation.

The baseline behavior is:
- `relevant` evidence -> answer from retrieved evidence only
- `ambiguous` evidence -> refuse with an explicit reason
- `irrelevant` evidence -> refuse with an explicit reason

## Why

- Retrieval quality must be judged explicitly before answer generation.
- In a tax/legal assistant, weak evidence is not a reason to answer cautiously; it is a reason to refuse.
- This creates an inspectable control point between retrieval and generation.

## Alternatives Considered

### Direct answer generation from top-k retrieval

Rejected.

Reason:
- It is too easy for weak or conflicting evidence to produce an answer that sounds confident but is not defensible.

### LLM-only grading as the first baseline

Rejected for the initial Phase 4 slice.

Reason:
- The first agent layer should remain runnable without API keys.
- Deterministic grading makes the control flow and tests easier to inspect.

## Tradeoffs

- Heuristic grading is less flexible than a strong model-based grader.
- The benefit is deterministic behavior, no external dependency, and explicit refusal logic that can be tested locally.

## Consequences

- The repository now has a concrete answer/refusal contract before any external LLM integration.
- Future model-based graders can be added behind the same control boundary.
- The system remains aligned with the assignment principle that abstention is a feature, not a failure.
