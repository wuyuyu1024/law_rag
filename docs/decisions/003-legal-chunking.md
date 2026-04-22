# ADR 003: Keep Legal Chunking Custom

## Context

The assignment explicitly warns that standard recursive chunking destroys legal hierarchy. The system must preserve article, paragraph, subparagraph, section, and citation context.

## Decision

Implement custom legal-aware chunking logic instead of relying on generic framework splitters.

## Why

- Statutes need chunk boundaries aligned with article and `lid` structure.
- Case law needs section-aware chunking, with canonical labels like `facts`, `reasoning`, and `holding`.
- Citation fields must remain traceable and resolvable end to end.

## Alternatives Considered

### Generic recursive text splitters

Rejected.

Reason:
- They optimize for token length, not legal meaning.
- They make it harder to guarantee that a chunk still knows it belongs to a specific article or paragraph.

### Fully outsourced chunking through LangChain or LlamaIndex

Rejected for the core chunking logic.

Reason:
- The legal chunking rules are a core part of the assignment, not generic infrastructure.
- Hiding them inside framework abstractions would make the design less inspectable and harder to defend.

## Tradeoffs

- Custom chunking means more code.
- The benefit is that the key legal behavior stays explicit, testable, and traceable.

## Consequences

- The chunking layer is domain-specific by design.
- It is easier to show interviewers exactly how legal hierarchy is preserved.
- Tests can target the legal structure directly instead of testing framework behavior indirectly.
