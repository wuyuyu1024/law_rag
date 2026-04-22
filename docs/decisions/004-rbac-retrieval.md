# ADR 004: RBAC Before Retrieval

## Context

The assignment requires strict RBAC and explicitly disallows systems where unauthorized material can leak into the answer path. A helpdesk employee must not retrieve or answer from restricted documents.

## Decision

Enforce RBAC at pre-retrieval candidate generation time.

In this repository, unauthorized chunks must not influence:
- lexical retrieval
- dense retrieval
- fusion
- reranking
- generation
- cache behavior
- evaluation outputs

## Why

- Filtering after retrieval is not sufficient.
- If unauthorized chunks are allowed to participate in scoring or ranking, they can still influence the system mathematically even if they are removed later.
- This is especially unacceptable in a tax/legal assistant with zero-hallucination expectations.

## Alternatives Considered

### Retrieve first, filter later

Rejected.

Reason:
- It violates the repository's security rule and the assignment's intent.
- It allows unauthorized content to affect similarity scoring, fusion, or reranking.

### Prompt-only security behavior

Rejected.

Reason:
- Access control is a retrieval and storage concern, not a prompt formatting concern.

## Tradeoffs

- Pre-retrieval filtering is stricter and can reduce recall if metadata is incomplete.
- That is acceptable because the system should abstain rather than answer from unauthorized or weak evidence.

## Consequences

- Security behavior is inspectable and testable.
- Retrieval APIs must carry role and authorization context explicitly.
- The design is defensible because it matches the assignment's strongest security constraint directly.
