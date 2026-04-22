# law-rag

Demo implementation for a technical assessment: a secure, citation-grounded, permission-aware RAG assistant for a national tax authority.

The primary requirements live in `assignment.md`. The implementation backlog lives in `TASKS.md`. If they disagree, follow `assignment.md`.

## Current Status

Phase 0 baseline is complete:
- repository structure exists
- the package is installable from `src/`
- baseline config defaults exist in Python and in `configs/`
- a reproducible legal demo corpus downloader is implemented
- a minimal pytest scaffold is in place

Phase 1 ingestion is implemented for the demo corpus:
- canonical normalized document schema exists
- raw Dutch law XML is parsed into article-level normalized records
- raw Rechtspraak XML is parsed into case-level normalized records
- synthetic internal policy and e-learning source fixtures are parsed into normalized records for architecture coverage

Phase 2 chunking is implemented for the demo corpus:
- legal-aware law chunking preserves article / `lid` / list-item citation context
- case-law chunking preserves section-aware boundaries and canonical `facts` / `reasoning` / `holding` labels
- synthetic internal policy and e-learning documents are chunked on section boundaries
- chunk export writes source-specific chunk files plus merged `data/chunks/legal_chunks.jsonl`

Phase 3 retrieval and RBAC are now implemented in a minimal but runnable form:
- retrieval-facing security contract enforces pre-retrieval RBAC
- exact lexical retrieval supports ECLI, article, paragraph, subparagraph, and citation-path lookups
- dense retrieval runs through local Qdrant-backed vector search
- hybrid retrieval fuses lexical and dense results with RRF
- retrieval outputs preserve inspectable scores, chunk IDs, and source references

Phase 4 baseline answer control is now implemented in a deterministic local form:
- retrieval evidence is graded as `relevant`, `ambiguous`, or `irrelevant`
- the system answers only from retrieved evidence graded as relevant
- ambiguous or weak evidence triggers explicit structured refusal reasons
- no external API key is required for the baseline answer/refusal flow
- corrective control flow now includes explicit query transformation, bounded retry, and inspectable state transitions

Generation and evaluation are still upcoming phases.

## Tooling

- Python environment and dependencies are managed with `uv`
- Node.js or frontend tooling should use `pnpm` if applicable

## Quick Start

```bash
uv run python -c "import tax_rag; print(tax_rag.__version__)"
uv run pytest -q
uv run python main.py
```

To refresh the demo raw corpus:

```bash
uv run python scripts/download_legal_demo_data.py \
  --config configs/data_sources.sample.json \
  --out-dir data/raw \
  --lock-file configs/demo_corpus.lock.json
```

## Repository Layout

The directories below exist today. Some contain only placeholders until later phases are implemented.

```text
configs/
data/
  raw/
  parsed/
  chunks/
  indexes/
  eval/
scripts/
src/tax_rag/
  common/
  schemas/
  ingestion/
  chunking/
  retrieval/
  security/
  agent/
  eval/
  app/
tests/
```

## Implemented So Far

`scripts/download_legal_demo_data.py` downloads a small Dutch legal demo corpus with:
- version-pinned law XML fetches
- exact ECLI case fetches
- SHA-256 hashing
- manifest generation
- lock-file verification for reproducibility

`scripts/parse_raw_data.py` parses that corpus into:
- `data/parsed/laws.jsonl`
- `data/parsed/cases.jsonl`
- `data/parsed/policies.jsonl`
- `data/parsed/e_learning.jsonl`
- `data/parsed/documents.jsonl`

`scripts/build_chunks.py` then exports legal-aware chunk datasets:
- `data/chunks/laws_chunks.jsonl`
- `data/chunks/case_chunks.jsonl`
- `data/chunks/policies_chunks.jsonl`
- `data/chunks/e_learning_chunks.jsonl`
- `data/chunks/legal_chunks.jsonl`

The internal-policy and e-learning records are synthetic stand-ins for the broader restricted/internal corpus described in the assignment.

## Config Defaults

The repo now includes config files for:
- chunking
- retrieval
- reranking
- security
- agent
- cache
- evaluation

Importable defaults are available from `tax_rag.common`.

The chunking config now documents the concrete Phase 2 strategy:
- laws split on article, `lid`, and list items while preserving citation context
- cases split on section and `paragroup` boundaries with canonical `facts` / `reasoning` / `holding` mapping
- synthetic internal-policy and e-learning sources split on section headings to preserve training/manual context

The retrieval config now documents the Phase 3 baseline:
- `qdrant` is the selected vector store for the demo dense path
- dense retrieval uses a local Qdrant collection with deterministic embeddings for repeatable tests
- hybrid fusion uses RRF with explicit top-k settings from `configs/retrieval.yaml`

The agent config now documents the Phase 4 baseline:
- explicit thresholds control evidence grading and answer/refusal gating
- refusal remains structured and inspectable
- the baseline answer layer stays local and deterministic
- bounded retry behavior is explicit and configuration-backed

## Vector DB Selection

For the assessment architecture, the selected vector database is **Qdrant**.

Why Qdrant fits this assignment:
- The hardest requirement is security-constrained retrieval: unauthorized chunks must be excluded before they can influence ranking, reranking, caching, or generation.
- Qdrant's payload model maps directly to this repository's metadata-first design, where each chunk carries `allowed_roles`, `security_classification`, `jurisdiction`, `source_type`, `article`, and `ecli`.
- Qdrant supports payload filtering, payload indexes, and filter-aware HNSW tuning, which makes pre-retrieval RBAC enforcement explicit and inspectable.
- Qdrant exposes concrete ANN controls such as HNSW `m`, `ef_construct`, search-time `ef`, and quantization settings, which aligns well with the assignment's request for specific operational parameters.
- The Python client and local mode are practical for a Python-first demo while still mapping cleanly to a production deployment path.

Recommended production-oriented Qdrant baseline:
- HNSW `m`: `32` as the default starting point, increase to `64` for higher recall on dense legal corpora.
- HNSW `ef_construct`: `200` for the baseline, increase to `512` for higher recall if indexing time is acceptable.
- Search-time `ef`: `128` for normal traffic, increase to `256` for high-precision legal queries or evaluation runs.
- Payload indexes: create indexes on `allowed_roles`, `security_classification`, `jurisdiction`, `source_type`, `article`, and `ecli` before bulk ingestion.
- Quantization: start with scalar quantization for memory reduction, and evaluate product quantization if the corpus approaches the upper end of the assignment's scale assumptions.
- Storage strategy: keep payload fields used in filtering indexed, and use on-disk vector storage plus quantization if RAM pressure becomes the bottleneck.

Why not Weaviate as the primary choice:
- Weaviate is a credible alternative. Its documentation describes efficient pre-filtered vector search, HNSW tuning, quantization, and built-in RBAC.
- However, this repository's core retrieval contract is chunk-level, metadata-driven authorization. Qdrant's point-plus-payload model maps more directly to that design and keeps the authorization and retrieval control plane more explicit in code.
- For this assessment, the deciding factor is not generic feature breadth. It is the ability to specify and defend pre-retrieval authorization with concrete filtering and indexing behavior.

Fair comparison note:
- Weaviate would still be a valid choice for the assessment, especially if the system prioritized built-in database authorization workflows or broader platform-level features.
- Qdrant is preferred here because it makes the chunk-level filtered-retrieval story simpler to reason about and easier to document with explicit retrieval and indexing parameters.

## Environment Variables

See `.env.example` for the current baseline variables:
- environment and log level
- data directory locations
- default role and retrieval settings
- demo security mode

## Assignment Mapping

The repo is structured around the four required modules from `assignment.md`:
- Ingestion and knowledge structuring
- Retrieval strategy
- Agentic RAG and self-healing
- Production ops, security, and evaluation

The current code covers the baseline, ingestion, and demo-scope chunking needed to start implementing retrieval, security, and answer control incrementally.

The implementation now also uses:
- `lxml` for XML parsing in ingestion and legal-aware chunking
- `pydantic` for schema validation and serialization boundaries
- `qdrant-client` for the dense retrieval backend
