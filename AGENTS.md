# AGENTS.md

## Project Purpose

This repository is a demo implementation for a technical assessment: designing a secure enterprise RAG assistant for a national tax authority.

The goal is not to build a generic chatbot. The goal is to build a permission-aware, citation-grounded, legal/tax retrieval system that can:

- preserve legal hierarchy during ingestion and chunking
- retrieve from statutes and case law with high precision
- enforce RBAC before retrieval and ranking
- generate answers only when evidence is sufficient
- refuse to answer when evidence is missing, conflicting, outdated, or unauthorized

## Source of Truth

- `assignment.md` is the primary source of truth for the assessment requirements.
- If implementation ideas conflict with `assignment.md`, follow `assignment.md`.
- This repo should stay aligned with the four required modules:
  1. Ingestion & Knowledge Structuring
  2. Retrieval Strategy
  3. Agentic RAG & Self-Healing
  4. Production Ops, Security & Evaluation
- The repository may use a reduced demo dataset, but the architecture, interfaces, and documentation should still address the full assignment scope.

## Scope

This repository is a demo, not a full production deployment.

Demo implementation scope:
- Public legal/tax source documents as the initial working dataset
- Dutch laws and Dutch case law as the first concrete demo corpus
- Python-first implementation
- Minimal but clear UI for demonstration
- Small evaluation set for regression checks

Assignment scope that must still be represented in architecture and docs:
- Internal policy guidelines and e-learning/wiki-style sources
- Classified/internal documents with role restrictions
- Large-scale indexing and retrieval assumptions for hundreds of thousands of documents and tens of millions of chunks
- Production-oriented evaluation, observability, caching, and security controls

Out of scope for the demo runtime unless explicitly requested:
- Full enterprise SSO / OAuth / OIDC integration
- Distributed production deployment
- Full observability stack implementation
- Multi-tenant infrastructure
- Real internal classified tax authority documents

When reducing scope for the demo:
- keep the architecture extensible to the full corpus described in `assignment.md`
- document what is simulated, stubbed, or represented by public stand-ins
- do not present demo simplifications as if the assignment requirement disappeared

## Core Design Principles

1. **Metadata-first**
   - Raw legal text must be normalized into structured documents before chunking.
   - Chunks must preserve legal citation context.
   - Legal hierarchy is part of the data model, not prompt-only context.

2. **Security-first retrieval**
   - Access control must constrain the candidate set before similarity scoring or ranking.
   - Unauthorized documents must never enter the searchable candidate set for a user.
   - Unauthorized content must not influence ranking, reranking, generation, caching, or evaluation outputs.

3. **Evidence-gated generation**
   - The system should answer only when evidence is sufficient.
   - Abstention is a feature, not a failure.
   - Retrieved evidence should be graded before answer generation.

4. **Citations are data, not prompt decoration**
   - Citation fields must be preserved in parsing, chunking, retrieval, and answer generation.
   - Answers must be traceable to source text.
   - The generator must not invent citations or legal identifiers.

5. **Concrete over generic**
   - The assignment asks for specific configurations, thresholds, and control-flow decisions.
   - Design docs and code should prefer explicit parameters over vague placeholders.

## Repository Conventions

### Language and Stack
- Use Python unless a task explicitly requires something else.
- Use `uv` for Python dependency management, virtual environments, lockfiles, and running Python scripts/tests.
- Use `pnpm` for Node.js or frontend tooling if a web UI or other JS-based component is added.
- Prefer standard, well-maintained libraries.
- Avoid introducing heavy dependencies unless clearly justified.
- If a library is added to satisfy an assignment requirement, document why that library was chosen over simpler alternatives.

### Data Format
- Keep raw source files immutable in `data/raw/`.
- Parsed/intermediate outputs should use JSONL unless there is a strong reason otherwise.
- Each parsed document and each chunk should have stable IDs.
- Metadata fields used in retrieval or security filtering must survive all serialization boundaries.

### Directory Responsibilities
- `src/tax_rag/common/`
  - shared utilities, constants, logging helpers, and simple cross-module types
- `src/tax_rag/schemas/`
  - shared data models and typed contracts for documents, chunks, retrieval outputs, citations, and answers
- `src/tax_rag/ingestion/`
  - raw source parsing and normalization only
- `src/tax_rag/chunking/`
  - document-to-chunk conversion only
- `src/tax_rag/retrieval/`
  - lexical retrieval, dense retrieval, fusion, reranking, citation resolution
- `src/tax_rag/security/`
  - role definitions, access policies, pre-retrieval filtering, security checks
- `src/tax_rag/agent/`
  - query transformation, evidence grading, retry/refusal logic, answer control
- `src/tax_rag/eval/`
  - evaluation datasets, metrics, regression runners
- `src/tax_rag/app/`
  - API/UI-facing code only
- `scripts/`
  - runnable entrypoints and pipeline scripts
- `configs/`
  - explicit retrieval, chunking, model, cache, and evaluation settings
- `tests/`
  - unit and small integration tests

Do not move responsibilities across modules without a clear reason.

## Required Metadata Fields

Where applicable, preserve the following fields.

### Document-level fields
- `doc_id`
- `source_type`
- `title`
- `jurisdiction`
- `effective_date`
- `security_classification`
- `allowed_roles`
- `source_path`

### Legal citation fields
- `article`
- `paragraph`
- `subparagraph`
- `citation_path`

### Case law fields
- `ecli`
- `court`
- `decision_date`
- `section_type`

### Chunk-level fields
- `chunk_id`
- `doc_id`
- `text`
- `citation_path`
- `source_type`
- `jurisdiction`
- `allowed_roles`

### Retrieval/output fields
- score fields should be inspectable
- source references should remain resolvable back to document and chunk IDs
- refusal reasons should be represented as explicit structured values when possible

## Security Rules

- RBAC filtering must happen before retrieval scoring/ranking is performed on a candidate set.
- Do not implement "retrieve first, filter later" as the main approach.
- Unauthorized content must not affect retrieval ranking, reranking, generation, caching, or evaluation.
- Role-based behavior should be testable.
- If security behavior is simulated in the demo, the docs must still explain the intended database-level enforcement point for the full system.

## Retrieval Rules

- Support both lexical/exact lookup and semantic retrieval.
- Legal identifiers such as article numbers and ECLI IDs must be treated carefully.
- Retrieval outputs should be explainable and traceable.
- Fusion strategy, candidate counts, reranker cutoffs, and key thresholds should be explicit in config or docs.
- Retrieval design should account for scale constraints described in `assignment.md`, even if the demo corpus is small.

## Generation Rules

- The generator must not invent citations.
- The generator must rely on retrieved evidence and explicit citation fields.
- If evidence is insufficient, ambiguous, conflicting, outdated, or unauthorized, prefer refusal.
- Refusal reasons should be explicit where possible.
- Query transformation and corrective retry behavior should be inspectable rather than hidden inside a single opaque prompt.

## Evaluation Expectations

Every meaningful feature should include at least minimal tests.

Priority tests:
- parser tests
- chunking tests
- retrieval tests
- RBAC tests
- citation integrity tests
- refusal behavior tests
- evaluation/regression runner tests where practical

Prefer small, deterministic tests.

In addition to tests, the repo should include:
- a small gold evaluation set
- a repeatable evaluation runner
- clearly named metrics tied back to assignment goals such as faithfulness, context precision, refusal correctness, and unauthorized retrieval prevention

## Definition of Done

A task is considered done when:
- code runs successfully
- outputs are written to the expected paths
- existing functionality is not broken
- minimal tests are added or updated
- configuration or README notes are updated when needed
- any affected architecture decision record in `docs/decisions/` is added or updated when the change modifies a meaningful design choice
- any demo simplification affecting assignment fidelity is called out explicitly

## Change Guidelines for Agents

When implementing tasks:
- keep changes focused and minimal
- do not rewrite unrelated modules
- avoid speculative abstractions
- prefer clear code over clever code
- preserve repository structure unless explicitly asked to change it
- prefer explicit configs and typed structures for retrieval/security behavior over hidden constants
- if a change affects a major design choice such as schema boundaries, XML parsing, chunking strategy, retrieval/security architecture, vector database selection, or other interviewer-relevant tradeoffs, update the corresponding file in `docs/decisions/`

If something is ambiguous:
- choose the simplest implementation that keeps future extension possible
- document assumptions clearly in code comments or task notes
- if the assignment requires a concrete parameter but the demo does not yet enforce it, record the intended value and rationale rather than omitting it
