# ADR 001: Schema Boundaries with Pydantic

## Context

The assignment requires metadata integrity across ingestion, chunking, retrieval, and answer generation. Fields such as `doc_id`, `citation_path`, `allowed_roles`, `article`, and `ecli` must survive every serialization boundary without drifting.

## Decision

Use `pydantic` models for the canonical schema layer:
- `NormalizedDocument`
- `ChunkRecord`
- retrieval request/result models

## Why

- The project handles untrusted inputs from XML, JSON fixtures, and retrieval payloads.
- The schema layer must validate required fields and preserve typed contracts.
- Later app/API work will benefit from predictable JSON serialization and stricter validation.

## Alternatives Considered

### Dataclasses only

Rejected as the long-term boundary model.

Reason:
- They were acceptable for the scaffold stage.
- They required manual validation and manual serialization control.
- As the system moved into retrieval and cross-module payload exchange, that became too brittle.

### Full framework-native models only

Rejected.

Reason:
- The repository should keep schema contracts explicit and framework-independent.

## Tradeoffs

- `pydantic` adds a dependency and some model verbosity.
- The benefit is stronger validation and cleaner serialization semantics at system boundaries.

## Consequences

- Schema failures happen earlier and more explicitly.
- Future API/UI work can reuse the same typed contracts.
- The design is easier to defend because metadata preservation is enforced in code, not only by convention.
