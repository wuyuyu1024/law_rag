# law-rag

Runnable architecture demo for the technical assessment in [assignment.md](./assignment.md): a secure, citation-grounded, permission-aware RAG assistant for a national tax authority.

The demo is intentionally smaller than the production target, but it implements the core control points: legal-aware chunking, pre-retrieval RBAC, hybrid retrieval, reranking, evidence-gated answering/refusal, semantic cache policy, evaluation, and promotion gates.

## Start Here

- [docs/index.md](./docs/index.md): recommended reading order
- [SUBMISSION.md](./SUBMISSION.md): main module-by-module assessment answer
- [docs/demo-script.md](./docs/demo-script.md): live presentation flow and what each demo case proves
- [docs/architecture.md](./docs/architecture.md): system diagram
- [docs/production-delta.md](./docs/production-delta.md): what remains before real deployment
- [docs/decisions/README.md](./docs/decisions/README.md): optional architecture decision appendix

## Quick Demo

```bash
uv run python scripts/run_interview_demo.py --dense-index-path data/indexes/qdrant
```

If the dense index is missing:

```bash
uv run python scripts/build_dense_index.py --recreate
```

The curated demo covers:

- exact statutory lookup with citation
- semantic retrieval for a 30 percent ruling question
- semantic cache miss/hit behavior
- RBAC refusal for a helpdesk role
- authorized restricted-source access for an inspector role
- outdated-evidence refusal

## Verification

```bash
uv run python -m pytest -q
uv run ruff check .
uv run mypy
uv run python scripts/run_eval.py --candidate-label local-demo --gate-promotion
```

Current local gate expectation: 19 gold cases pass with zero unauthorized retrieval failures.

## Build The Demo Corpus

```bash
uv run python scripts/download_legal_demo_data.py \
  --config configs/data_sources.sample.json \
  --out-dir data/raw \
  --lock-file configs/demo_corpus.lock.json
uv run python scripts/parse_raw_data.py
uv run python scripts/build_chunks.py
uv run python scripts/build_dense_index.py --recreate
```

## Optional Services

The Python demo and tests do not require containers. Use Compose only when showing the production-shaped Qdrant/Redis infrastructure path:

```bash
docker compose up -d qdrant redis
```

Optional API:

```bash
uv run uvicorn tax_rag.api.main:app --reload
```

Optional real reranker dependency:

```bash
uv sync --extra rerank
```

## Repository Map

```text
configs/              explicit chunking, retrieval, reranking, security, cache, eval settings
data/                 raw, parsed, chunked, indexed, and evaluation artifacts
docs/                 presentation docs and ADR appendix
scripts/              runnable pipeline, demo, benchmark, and eval commands
src/tax_rag/          package source
tests/                deterministic unit and integration tests
```

## Scope Note

This is a runnable demo plus production blueprint, not a full production deployment. The demo corpus is small and partly synthetic; the default embedding and reranker are deterministic local baselines. See [docs/production-delta.md](./docs/production-delta.md) for the remaining production work.
