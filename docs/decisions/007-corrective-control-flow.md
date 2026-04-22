# ADR 007: Corrective Control Flow with Inspectable States

## Context

The assignment asks for a state-machine-like control loop rather than a single opaque retrieval-and-answer step. The system should be able to understand or transform a query, retrieve evidence, grade it, and either answer, retry, or refuse.

## Decision

Introduce an explicit local control flow with inspectable states:
- `understood`
- `transformed`
- `retrieved`
- `graded`
- `retrying`
- `answered`
- `refused`

The initial deterministic strategies are:
- query decomposition for obvious multi-part questions
- one bounded lexical retry for structured legal identifiers when the first pass is weak

## Why

- The retrieval and answer path should be debuggable and explainable.
- Legal queries often contain exact identifiers mixed with natural language, so a focused retry path is useful.
- Multi-part questions should be decomposed explicitly instead of assuming one retrieval pass covers all sub-questions.

## Alternatives Considered

### Single-pass retrieval and grading only

Rejected.

Reason:
- It does not satisfy the assignment's corrective-RAG spirit.
- It makes query transformation and retry logic invisible.

### Full LLM-driven agent loop as the first implementation

Rejected for the baseline.

Reason:
- It would make the control flow less deterministic and harder to test locally.
- A local state machine provides a safer base for later model-backed upgrades.

## Tradeoffs

- The deterministic control flow is narrower than a model-driven planner.
- The benefit is explicit transitions, local testability, and no API-key dependency.

## Consequences

- The agent layer now has an inspectable backbone that later LangGraph-style orchestration can replace or wrap.
- Query transformation is explicit rather than hidden inside a prompt.
- Retry behavior is bounded and easier to defend in an interview.
