# law-rag

Demo implementation for a technical assessment: a secure, citation-grounded, permission-aware RAG assistant for a national tax authority.

The primary requirements live in `assignment.md`. The implementation backlog lives in `TASKS.md`. If they disagree, follow `assignment.md`.

## Current Status

Phase 0 is the current baseline:
- repository structure exists
- the package is installable from `src/`
- baseline config defaults exist in Python and in `configs/`
- a reproducible legal demo corpus downloader is implemented
- a minimal pytest scaffold is in place

Phase 1 ingestion is now partially implemented:
- canonical normalized document schema exists
- raw Dutch law XML is parsed into article-level normalized records
- raw Rechtspraak XML is parsed into case-level normalized records
- internal policy and e-learning sources are represented by fixture-backed adapters for architecture coverage

Chunking, retrieval, RBAC enforcement, generation, and evaluation are still upcoming phases.

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

This remains a demo-scope stand-in for the broader corpus described in the assignment.

## Config Defaults

Phase 0 includes placeholder config files for:
- chunking
- retrieval
- reranking
- security
- cache
- evaluation

Importable defaults are available from `tax_rag.common`.

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

The current code only establishes the baseline needed to start implementing those modules safely and incrementally.
