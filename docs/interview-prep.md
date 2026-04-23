# Interview Prep

This file is a short defense guide for the main design choices in the repository.

## Five-Minute Walkthrough

Use this order:

1. Problem and constraints
The assistant is for a national tax authority, so the system is not a generic chatbot. The hard constraints are legal hierarchy preservation, strict RBAC before retrieval, exact citations, and abstention when evidence is weak or unauthorized.

2. Data model
I normalized raw sources into canonical document and chunk schemas so the retrieval system works on structured legal records, not only raw text. That is why fields like `doc_id`, `citation_path`, `allowed_roles`, `article`, and `ecli` are first-class data fields.

3. Security model
RBAC is enforced before retrieval candidates are ranked. Unauthorized chunks do not enter lexical retrieval, dense retrieval, fusion, reranking, generation, cache behavior, or evaluation.

4. Retrieval model
The retrieval path is hybrid. Lexical retrieval handles exact identifiers like ECLI and article references. Dense retrieval handles semantic recall. RRF combines them without fragile score calibration, and a deterministic reranker improves semantic ranking while keeping scores inspectable.

5. Infrastructure choices
I used `lxml` for stronger XML handling, `pydantic` for schema boundaries, and Qdrant for dense retrieval because the assignment needs explicit filtered vector search and concrete ANN settings.

6. Demo vs production
The runtime corpus is small and partly simulated, but the architecture is shaped around the full assignment: restricted documents, large-scale chunk counts, pre-retrieval authorization, and explicit retrieval controls.

Use this clarification if pressed on scale:
I kept the runnable corpus small on purpose so the demo stays inspectable. I represent scale mainly in the architecture and control plane: filtered ANN retrieval, payload indexes, bounded top-k, persistent indexing, and explicit latency budgets. The local benchmark is for catching bottlenecks and validating fixes, not for pretending I reproduced a 20M-chunk production environment on a demo machine.

## Likely Questions

### Why did you keep legal chunking custom?

Short answer:
Because legal hierarchy is part of the assignment, not an implementation detail. Generic splitters optimize for token length, but I needed chunks that remain traceable to article, paragraph, subparagraph, or case section.

Repo references:
- `src/tax_rag/chunking/legal_chunker.py`
- `src/tax_rag/chunking/case_chunker.py`

### Why enforce RBAC before retrieval instead of after?

Short answer:
Because post-filtering still allows unauthorized chunks to influence scoring and ranking. The assignment requires that unauthorized material must not affect retrieval or generation at all, so the filter must apply before candidate scoring matters.

Repo references:
- `src/tax_rag/security/contract.py`
- `src/tax_rag/security/rbac.py`

### Why did you choose Qdrant over Weaviate?

Short answer:
Weaviate is a valid alternative, but Qdrant maps more directly to the chunk-plus-payload model in this repository. I wanted explicit control over payload filtering, HNSW settings, and metadata-driven authorization at retrieval time.

Repo references:
- `README.md`
- `src/tax_rag/retrieval/dense.py`
- `docs/decisions/005-vector-db-and-hybrid-retrieval.md`

### Why hybrid retrieval instead of dense-only retrieval?

Short answer:
Legal search includes exact identifiers and semantic concepts. Dense retrieval is useful for semantic recall, but article numbers and ECLI references need a precise lexical path. Hybrid retrieval covers both and is more defensible for this domain.

Repo references:
- `src/tax_rag/retrieval/lexical.py`
- `src/tax_rag/retrieval/dense.py`
- `src/tax_rag/retrieval/hybrid.py`

### Why did you use RRF instead of weighted score blending?

Short answer:
RRF is simpler and more robust as an initial legal-search baseline. It combines rank evidence from lexical and dense retrieval without relying on fragile score calibration between very different scorers.

Repo references:
- `src/tax_rag/retrieval/hybrid.py`
- `src/tax_rag/common/config.py`

### Why add a deterministic reranker instead of a model-based reranker immediately?

Short answer:
Because the immediate problem was evaluation quality, not model sophistication. I needed a stronger semantic baseline that stayed local, testable, and inspectable, so I added semantic normalization plus a deterministic reranker first. That improves retrieval now without hiding behavior inside an opaque model call.

Repo references:
- `src/tax_rag/retrieval/semantic.py`
- `src/tax_rag/retrieval/rerank.py`
- `docs/decisions/009-deterministic-reranking-and-semantic-normalization.md`

### Why use Pydantic if it did not reduce much code?

Short answer:
The point was not line-count reduction. The point was to make schema validation and serialization more reliable at system boundaries. Most of the remaining code is domain logic, not generic plumbing.

Repo references:
- `src/tax_rag/schemas/document.py`
- `src/tax_rag/schemas/chunk.py`
- `src/tax_rag/schemas/retrieval.py`

### Why use lxml?

Short answer:
The corpus is XML-heavy and structure-sensitive. I needed a stronger XML tool than the minimal standard-library parser because the system must preserve legal structure, namespace-heavy case law content, and later XPath-friendly extensibility.

Repo references:
- `src/tax_rag/ingestion/parser_laws.py`
- `src/tax_rag/ingestion/parser_cases.py`

### Why refuse instead of answering weakly?

Short answer:
Because the assignment is zero-hallucination and citation-grounded. In a tax/legal system, weak, conflicting, or outdated evidence should stop the answer path. Refusal is a safety feature, not a UX failure.

Repo references:
- `src/tax_rag/agent/evidence.py`
- `src/tax_rag/agent/baseline.py`
- `docs/decisions/006-evidence-gating-and-refusal.md`

### Why add an explicit control flow instead of one retrieval call plus answer generation?

Short answer:
Because the assignment asks for agentic and corrective behavior, not a linear pipeline. I made the control states explicit so query transformation, retrieval, grading, retry, answer, and refusal are inspectable and testable.

Repo references:
- `src/tax_rag/agent/control.py`
- `src/tax_rag/agent/transform.py`
- `docs/decisions/007-corrective-control-flow.md`

### What is still missing?

Short answer:
The main next steps are semantic cache design, upgrading the deterministic reranker to a real learned reranker, improving the remaining exact and refusal edge cases in the eval set, and only then adding a stronger generation layer. The current system already has evidence grading, corrective control flow, promotion gating, and structured trace artifacts.

Repo references:
- `TASKS.md`
- `src/tax_rag/agent/`
- `src/tax_rag/eval/`

### How do you evaluate the system before changing retrieval or models?

Short answer:
I added a deterministic gold-set runner first so retrieval, refusal, and citation behavior can be checked locally and repeatedly. Candidate runs can now be gated against explicit thresholds and a prior approved baseline report before promotion. The current faithfulness and context-precision signals are explicit proxies, and the design is intended to be extended later with Ragas or DeepEval rather than replaced.

Repo references:
- `data/eval/gold_questions.jsonl`
- `src/tax_rag/eval/runner.py`
- `scripts/run_eval.py`
- `docs/decisions/008-deterministic-evaluation-baseline.md`

## Fast Defense Pattern

When you answer a design question, use this pattern:

1. Name the assignment constraint.
2. State the decision.
3. State the rejected alternative.
4. Explain the tradeoff you accepted.

Example:

The assignment requires RBAC before retrieval influence. I therefore filtered candidates before lexical and dense ranking rather than retrieving first and filtering later. That trades some recall if metadata is incomplete, but in this domain abstention is safer than leaking restricted evidence.

## What To Memorize

If time is limited, memorize these points:

- This is not a generic chatbot. It is a secure legal retrieval system.
- Metadata preservation is a first-class design rule.
- RBAC is pre-retrieval, not post-retrieval.
- Lexical retrieval is necessary for legal identifiers.
- Dense retrieval is necessary for semantic recall.
- Hybrid retrieval with RRF is the initial baseline.
- Deterministic semantic reranking is the current quality-improvement layer.
- Qdrant was chosen because filtered retrieval is the core requirement.
- Refusal is a feature in a zero-hallucination domain.
