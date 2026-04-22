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
- internal policy and e-learning sources are represented by fixture-backed adapters for architecture coverage

Phase 2 chunking is implemented for the demo corpus:
- legal-aware law chunking preserves article / `lid` / list-item citation context
- case-law chunking preserves section-aware boundaries and canonical `facts` / `reasoning` / `holding` labels
- chunk export writes `data/chunks/laws_chunks.jsonl`, `data/chunks/case_chunks.jsonl`, and `data/chunks/legal_chunks.jsonl`

Retrieval, RBAC enforcement, generation, and evaluation are still upcoming phases.

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
- `data/parsed/documents.jsonl`

`scripts/build_chunks.py` then exports legal-aware chunk datasets:
- `data/chunks/laws_chunks.jsonl`
- `data/chunks/case_chunks.jsonl`
- `data/chunks/legal_chunks.jsonl`

This remains a demo-scope stand-in for the broader corpus described in the assignment.

## Config Defaults

The repo now includes config files for:
- chunking
- retrieval
- reranking
- security
- cache
- evaluation

Importable defaults are available from `tax_rag.common`.

The chunking config now documents the concrete Phase 2 strategy:
- laws split on article, `lid`, and list items while preserving citation context
- cases split on section and `paragroup` boundaries with canonical `facts` / `reasoning` / `holding` mapping

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
