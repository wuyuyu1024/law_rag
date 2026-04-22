# TASKS.md

This file breaks the project into small, incremental implementation tasks suitable for iterative development with Codex.

The guiding rule is:
**always keep the project runnable, even if incomplete.**

This backlog is organized to stay faithful to `assignment.md` while still supporting a smaller demo dataset. Required assignment items remain required even if the first implementation is lightweight or simulated.

---

# Cross-Cutting Assignment Constraints

The three strict system constraints from `assignment.md` are not optional feature ideas. They are cross-cutting requirements that should stay visible across phases.

## Constraint A - Zero-Hallucination Tolerance

Every answer must stay grounded in retrieved evidence and exact citations. If evidence is weak, ambiguous, conflicting, outdated, or unauthorized, the system should refuse rather than guess.

Primary task coverage:
- Phase 1 schema and metadata preservation
- Phase 2 legal-aware chunking
- Phase 3 citation-preserving retrieval
- Phase 4 evidence grading, corrective control flow, and refusal reasons
- Phase 5 evaluation for citation presence, faithfulness, and refusal correctness

## Constraint B - Security and Access Control

RBAC must apply before retrieval influence. Unauthorized documents must not affect ranking, reranking, generation, cache behavior, or evaluation.

Primary task coverage:
- Phase 1 source and security metadata modeling
- Phase 2 chunk-level `allowed_roles` preservation
- Phase 3 RBAC-constrained candidate generation
- Phase 5 cache isolation, evaluation, and observability of security behavior

## Constraint C - High Performance at Scale

The architecture must support roughly 500k documents and 20M+ chunks while keeping uncached-path TTFT under `1.5s`. Cache is an optimization, not the primary defense for the latency target.

Primary task coverage:
- Phase 3 vector database selection and scale assumptions
- Phase 3 concrete ANN/index settings, quantization, and latency budget
- Phase 3 persistent vector index build/load path for the demo architecture
- Phase 3 uncached-path latency benchmark harness
- Phase 5 semantic cache as an additional optimization layer

---

# Phase 0 - Repository Skeleton

## Task 0.1 - Create repository structure
Create the initial folder structure:

- `configs/`
- `data/raw/`
- `data/parsed/`
- `data/chunks/`
- `data/eval/`
- `scripts/`
- `src/tax_rag/common/`
- `src/tax_rag/schemas/`
- `src/tax_rag/ingestion/`
- `src/tax_rag/chunking/`
- `src/tax_rag/retrieval/`
- `src/tax_rag/security/`
- `src/tax_rag/agent/`
- `src/tax_rag/eval/`
- `src/tax_rag/app/`
- `tests/`

### Acceptance criteria
- Folder structure exists
- Imports work cleanly
- No business logic required yet

---

## Task 0.2 - Create project metadata and setup
Add:

- `README.md`
- `pyproject.toml`
- `.env.example`

### Acceptance criteria
- Python package installs locally
- README has basic project description and assignment mapping
- Environment variables are documented

---

## Task 0.3 - Add base testing setup
Set up basic testing with `pytest`.

### Acceptance criteria
- `pytest` runs successfully
- At least one placeholder test exists

---

## Task 0.4 - Add explicit config files
Create config files or config models for:

- chunking
- retrieval
- reranking
- security
- cache
- evaluation

### Acceptance criteria
- Configs are defined in one place
- Defaults are importable
- Assignment-specific parameters have a home even before full implementation

---

# Phase 1 - Data Model and Parsed Documents

## Task 1.1 - Define canonical document schema
Create a shared schema/model for normalized documents.

Suggested fields:
- `doc_id`
- `source_type`
- `title`
- `jurisdiction`
- `effective_date`
- `article`
- `paragraph`
- `subparagraph`
- `citation_path`
- `ecli`
- `court`
- `decision_date`
- `section_type`
- `security_classification`
- `allowed_roles`
- `text`
- `source_path`

### Acceptance criteria
- Schema is defined in one place
- Schema is importable across modules
- Minimal validation exists

---

## Task 1.2 - Model assignment source types
Represent the corpus categories from `assignment.md`, even if the initial dataset is smaller.

Source types to support:
- legislation and regulations
- case law and jurisprudence
- internal policy guidance
- e-learning and wiki-like content

### Acceptance criteria
- Source type enum or constants cover all assignment categories
- Demo-only source limitations are documented separately from schema support
- Tests confirm unsupported categories are not silently dropped

---

## Task 1.3 - Parse case law XML files
Implement parsing for `data/raw/cases/*.xml`.

### Output
- `data/parsed/cases.jsonl`

### Acceptance criteria
- Each record includes `doc_id`, `source_type`, `title`, `jurisdiction`, `ecli`, `text`
- Source path is preserved
- At least 2 parser tests exist

---

## Task 1.4 - Parse law XML files
Implement parsing for `data/raw/laws/*.xml`.

### Output
- `data/parsed/laws.jsonl`

### Acceptance criteria
- Each record includes `doc_id`, `source_type`, `title`, `jurisdiction`, `text`
- Best-effort extraction of legal structure fields
- At least 2 parser tests exist

---

## Task 1.5 - Add placeholder adapters for policy/wiki-like sources
Add a minimal normalization path for internal-policy-style and wiki/e-learning-style documents so the architecture reflects the full assignment corpus.

### Acceptance criteria
- Adapter interfaces exist even if backed by fixture data only
- Normalized outputs conform to the shared schema
- README or docstring notes what is simulated in the demo

---

## Task 1.6 - Merge parsed documents
Merge parsed sources into a unified dataset.

### Output
- `data/parsed/documents.jsonl`

### Acceptance criteria
- Supported source types appear in one unified format
- IDs are stable
- Invalid records are skipped or logged clearly

---

# Phase 2 - Legal-Aware Chunking

## Task 2.1 - Implement law chunker
Chunk statutes/regulations using legal structure, not fixed token size alone.

Preferred hierarchy:
- article
- paragraph
- subparagraph

### Acceptance criteria
- Each chunk preserves `citation_path`
- Chunks remain human-readable
- Chunk text is not arbitrary fragments

---

## Task 2.2 - Implement case law chunker
Chunk case law using structured sections where possible.

Preferred structure:
- facts
- reasoning
- holding
- paragraph-based fallback

### Acceptance criteria
- Each chunk preserves `ecli`
- Section type is kept where available
- Chunk boundaries are meaningful

---

## Task 2.3 - Build chunk metadata
Add metadata builder for chunk-level records.

Required chunk fields:
- `chunk_id`
- `doc_id`
- `text`
- `citation_path`
- `source_type`
- `jurisdiction`
- `allowed_roles`

### Acceptance criteria
- Chunk IDs are deterministic or stable
- Metadata is complete
- No chunk is missing parent document linkage

---

## Task 2.4 - Add chunking configuration examples
Provide concrete chunking config or pseudocode that shows how legal metadata is preserved.

### Acceptance criteria
- Example ties chunk text back to article/paragraph context
- Config or pseudocode is close enough for implementation handoff
- README or `configs/` captures the chosen strategy

---

## Task 2.5 - Export final chunk dataset
Combine all chunk outputs.

### Output
- `data/chunks/legal_chunks.jsonl`

### Acceptance criteria
- File is valid JSONL
- Includes both law and case chunks
- Ready for indexing/retrieval

---

# Phase 3 - Retrieval Architecture and Scale

## Task 3.1 - Select vector database and document scale assumptions
Choose the vector database for the assignment architecture and record why it fits 500k documents / 20M+ chunks.

### Acceptance criteria
- One vector DB is selected explicitly
- Tradeoffs versus at least one alternative are documented
- The doc addresses memory, latency, and operational fit

---

## Task 3.2 - Define index configuration for scale
Specify concrete index settings for the chosen vector store.

Examples:
- HNSW parameters such as `m` and `ef_construct`
- search-time parameters such as `ef_search`
- quantization or compression strategy
- sharding or partitioning assumptions if needed

### Acceptance criteria
- Concrete parameter values are recorded
- Rationale is given for recall/latency tradeoffs
- OOM and latency-spike mitigation is addressed explicitly

---

## Task 3.3 - Implement exact/keyword retrieval
Add a lexical retrieval path for:
- article numbers
- ECLI references
- keyword search

### Acceptance criteria
- Exact identifiers can be matched
- Results include citation metadata
- Retrieval is testable

---

## Task 3.4 - Implement dense retrieval
Add embedding-based retrieval over chunk text.

### Acceptance criteria
- Embeddings can be built for all chunks
- Similarity search returns ranked chunks
- Retrieval API is documented

---

## Task 3.5 - Implement RBAC-constrained candidate generation
Apply role-based filtering before dense or lexical results are finalized, and before unauthorized items can influence ranking.

Example roles:
- `helpdesk`
- `inspector`
- `legal_counsel`

### Acceptance criteria
- Unauthorized chunks are excluded from the candidate set used for final ranking
- Retrieval tests cover multiple roles
- No "retrieve first, filter later" main path
- Security notes explain the intended database-level enforcement point

---

## Task 3.6 - Implement hybrid retrieval
Combine lexical and dense retrieval into a single interface.

Suggested API:
- `retrieve(query: str, role: str, top_k: int)`

### Acceptance criteria
- Hybrid retrieval returns a ranked list
- Exact lookup and semantic lookup both work reasonably
- Retrieval behavior is testable

---

## Task 3.7 - Define hybrid fusion strategy
Choose and document how lexical and dense scores are combined for the legal domain.

Examples:
- Reciprocal Rank Fusion
- weighted blend with an explicit `alpha`

### Acceptance criteria
- Fusion strategy is explicit
- Parameters are concrete
- Rationale covers legal identifier lookups versus semantic concepts

---

## Task 3.8 - Add reranking layer
Add a reranking step for candidate chunks.

### Acceptance criteria
- Candidate set is reranked before final answering
- Inputs/outputs are inspectable
- Can be disabled for debugging
- Reranker model choice is documented
- Initial retrieval Top-K and final reranker Top-K are explicit

---

## Task 3.9 - Add citation resolver
Resolve chunk IDs back into displayable citations.

### Acceptance criteria
- Output citation strings are stable
- Citation formatting is consistent
- Used by answering layer later

---

## Task 3.10 - Record TTFT and latency budget assumptions
Document the latency budget for retrieval and generation to stay within the assignment target.

### Acceptance criteria
- TTFT target of under 1.5 seconds is acknowledged
- Retrieval, reranking, and generation budget assumptions are broken down
- Notes distinguish demo performance from target production architecture

---

## Task 3.11 - Add persistent vector index build/load path
Move the dense retrieval path from demo-only local in-memory indexing toward a persistent deployment-shaped path.

Examples:
- explicit collection creation
- payload index creation
- index build/load scripts
- collection existence checks
- repeatable local/dev startup flow

### Acceptance criteria
- Dense retrieval can run without rebuilding the full index on every query
- Payload fields used for filtering are explicitly indexed
- README or docs explain the demo path versus the intended production path
- The implementation still preserves pre-retrieval RBAC behavior

---

## Task 3.12 - Add uncached-path latency benchmark harness
Create a repeatable benchmark that measures the uncached request path against the assignment TTFT target.

At minimum, measure:
- request parsing / setup
- lexical retrieval
- dense retrieval
- fusion
- reranking
- evidence grading
- answer construction or first-token proxy

### Acceptance criteria
- Benchmark can be run locally with a clear entrypoint
- Per-stage timings are reported, not only a single total
- Results distinguish cached versus uncached paths where relevant
- The benchmark records whether the uncached path stays under the `1.5s` target
- Notes distinguish demo benchmark results from production-scale expectations

---

# Phase 4 - Agentic RAG and Self-Healing

## Task 4.1 - Implement answer generation baseline
Generate answers from retrieved evidence only.

### Acceptance criteria
- Answers include citations
- Answers rely on retrieved evidence
- No fabricated citation placeholders

---

## Task 4.2 - Implement query transformation
Handle complex, multi-part tax questions before retrieval.

Possible techniques:
- query decomposition
- HyDE
- structured legal identifier extraction

### Acceptance criteria
- At least one transformation path is implemented
- Behavior is inspectable
- Tests cover a multi-part query

---

## Task 4.3 - Implement evidence grader
Classify retrieval quality into:
- `relevant`
- `ambiguous`
- `irrelevant`

### Acceptance criteria
- Grader output is explicit
- Logic is testable
- Grader result is used downstream

---

## Task 4.4 - Implement corrective RAG control flow
Add a state-machine-like control flow for:

- understand or transform query
- retrieve evidence
- grade evidence
- answer / retry / refuse

### Acceptance criteria
- Control flow states are explicit in code
- Design is compatible with a LangGraph-style state machine
- Transitions are inspectable for debugging

---

## Task 4.5 - Define fallback actions for evidence grades
Specify exact system behavior when evidence is:

- `relevant`
- `ambiguous`
- `irrelevant`

### Acceptance criteria
- Relevant evidence leads to answer generation
- Ambiguous evidence triggers a bounded retry or clarification path
- Irrelevant evidence triggers refusal
- Actions are documented and testable

---

## Task 4.6 - Add refusal reasons
Support structured refusal reasons such as:
- no authorized source available
- insufficient evidence
- conflicting evidence
- outdated evidence

### Acceptance criteria
- Refusals are not generic
- Reason is visible in output
- Can be demonstrated in UI later

---

# Phase 5 - Production Ops, Security, and Evaluation

## Task 5.1 - Design semantic cache policy
Prototype a safe semantic cache for FAQ-like queries.

### Acceptance criteria
- Cache scope is documented
- Unsafe query classes are excluded
- Cosine similarity threshold is explicit and justified for tax/legal use

---

## Task 5.2 - Implement cache key and authorization strategy
Ensure cache behavior does not cross role or authorization boundaries.

### Acceptance criteria
- Cache keys account for role and relevant retrieval context
- Unauthorized answers cannot be served across roles
- Tests cover at least one cache isolation scenario

---

## Task 5.3 - Add evaluation runner
Create a script to run the system against a gold set.

### Acceptance criteria
- Outputs summary metrics
- Stores detailed results for inspection
- Can be rerun after changes

---

## Task 5.4 - Create small gold evaluation set
Create `data/eval/gold_questions.jsonl`.

Include:
- exact legal lookup
- semantic legal lookup
- multi-part questions
- unauthorized-role questions
- should-refuse questions

### Acceptance criteria
- At least 10-20 questions
- Each record includes expected behavior
- Dataset is easy to extend

---

## Task 5.5 - Add core regression metrics
Track at least:
- answerable vs refused
- citation presence
- unauthorized retrieval failures
- exact lookup success
- semantic retrieval success
- faithfulness
- context precision

### Acceptance criteria
- Metrics are printed clearly
- Failures are inspectable
- Regressions are easy to spot
- Metrics map back to assignment requirements

---

## Task 5.6 - Add pre-deployment evaluation hook
Define how new embedding models or LLMs are evaluated before promotion.

Examples:
- local script
- CI job
- gated report

### Acceptance criteria
- Evaluation entrypoint is documented
- Promotion criteria are explicit
- Metric names reference tools such as DeepEval or Ragas where relevant

---

## Task 5.7 - Add observability and trace logging
Log enough information to inspect retrieval, grading, retries, refusals, and citation use.

### Acceptance criteria
- Retrieval decisions are logged
- Grader outputs and refusal causes are inspectable
- Logging is useful for demo and regression debugging

---

# Phase 6 - Demo UX

## Task 6.1 - Create minimal demo entrypoint
Build a runnable demo app or CLI flow.

### Acceptance criteria
- User can submit a query
- User can choose a role
- System returns answer or refusal

---

## Task 6.2 - Add evidence display
Show top retrieved chunks and citations.

### Acceptance criteria
- Retrieved evidence is visible
- Citation paths are visible
- Makes debugging easier

---

## Task 6.3 - Add role selector
Allow role switching in demo.

### Acceptance criteria
- Same query can produce different results for different roles
- This is easy to demonstrate live

---

## Task 6.4 - Add refusal explanation display
When the system refuses, surface the reason.

### Acceptance criteria
- Refusal reason is visible in UI/CLI
- Behavior is inspectable and demo-friendly

---

# Nice-to-Have Tasks

These are improvements beyond the explicit assignment baseline.

## Task N.1 - Add richer legal citation formatting
Support multiple display formats for statutes and case law citations.

## Task N.2 - Add stronger policy/wiki parsers
Improve parsing fidelity for internal-policy-style and wiki-like documents.

## Task N.3 - Add more advanced observability backend
Export traces/metrics to a dedicated observability system.

## Task N.4 - Add retrieval error analysis tooling
Group failures by parser, chunking, retrieval, security, or generation cause.

---

# Recommended First Tasks for Codex

Start with these in order:

1. Task 0.1 - Create repository structure
2. Task 0.2 - Create project metadata and setup
3. Task 0.3 - Add base testing setup
4. Task 0.4 - Add explicit config files
5. Task 1.1 - Define canonical document schema
6. Task 1.3 - Parse case law XML files
7. Task 1.4 - Parse law XML files
8. Task 1.6 - Merge parsed documents
9. Task 2.1 - Implement law chunker
10. Task 2.2 - Implement case law chunker

Do not start with the full agent loop or demo UI before parsed documents, chunking, and retrieval basics are stable.
