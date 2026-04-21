Tooling:
- Python environment and dependencies are managed with `uv`.
- Node.js or frontend tooling should use `pnpm` if applicable.

tax-rag-demo/
├── assignment.md
├── AGENTS.md
├── TASKS.md
├── README.md
├── pyproject.toml
├── .env.example
│
├── configs/
│   ├── app.yaml
│   ├── chunking.yaml
│   ├── retrieval.yaml
│   ├── security.yaml
│   ├── indexing.yaml
│   └── eval.yaml
│
├── data/
│   ├── raw/
│   │   ├── laws/
│   │   ├── cases/
│   │   └── manifest.json
│   ├── parsed/
│   │   ├── laws.jsonl
│   │   ├── cases.jsonl
│   │   └── documents.jsonl
│   ├── chunks/
│   │   ├── laws_chunks.jsonl
│   │   ├── case_chunks.jsonl
│   │   ├── legal_chunks.jsonl
│   │   └── citation_map.json
│   ├── indexes/
│   │   ├── embeddings/
│   │   ├── lexical/
│   │   └── metadata/
│   └── eval/
│       ├── gold_questions.jsonl
│       ├── expected_behavior.jsonl
│       └── eval_runs/
│
├── scripts/
│   ├── download_legal_demo_data.py
│   ├── parse_raw_data.py
│   ├── build_chunks.py
│   ├── build_index.py
│   ├── run_demo.py
│   ├── run_eval.py
│   └── inspect_data.py
│
├── src/
│   └── tax_rag/
│       ├── __init__.py
│       │
│       ├── common/
│       │   ├── logging.py
│       │   ├── utils.py
│       │   ├── constants.py
│       │   └── types.py
│       │
│       ├── schemas/
│       │   ├── document.py
│       │   ├── chunk.py
│       │   ├── citation.py
│       │   ├── retrieval.py
│       │   └── answer.py
│       │
│       ├── ingestion/
│       │   ├── parser_laws.py
│       │   ├── parser_cases.py
│       │   ├── normalizer.py
│       │   └── merge_documents.py
│       │
│       ├── chunking/
│       │   ├── legal_chunker.py
│       │   ├── case_chunker.py
│       │   ├── metadata_builder.py
│       │   └── citation_builder.py
│       │
│       ├── indexing/
│       │   ├── embeddings.py
│       │   ├── lexical_index.py
│       │   ├── vector_store.py
│       │   ├── qdrant_store.py
│       │   └── upsert.py
│       │
│       ├── retrieval/
│       │   ├── exact_search.py
│       │   ├── dense_search.py
│       │   ├── hybrid_search.py
│       │   ├── reranker.py
│       │   ├── filters.py
│       │   └── citation_resolver.py
│       │
│       ├── security/
│       │   ├── roles.py
│       │   ├── policies.py
│       │   ├── access_context.py
│       │   └── retrieval_filter.py
│       │
│       ├── agent/
│       │   ├── query_transform.py
│       │   ├── grader.py
│       │   ├── control_loop.py
│       │   ├── refusal.py
│       │   └── answer_generator.py
│       │
│       ├── cache/
│       │   └── semantic_cache.py
│       │
│       ├── eval/
│       │   ├── dataset.py
│       │   ├── runner.py
│       │   ├── metrics.py
│       │   └── regression.py
│       │
│       └── app/
│           ├── api.py
│           ├── ui.py
│           └── demo_service.py
│
├── tests/
│   ├── test_parser_laws.py
│   ├── test_parser_cases.py
│   ├── test_chunking.py
│   ├── test_citations.py
│   ├── test_retrieval.py
│   ├── test_rbac.py
│   ├── test_agent_flow.py
│   └── test_eval_runner.py
│
└── notebooks/
    ├── 01_inspect_raw_data.ipynb
    ├── 02_preview_chunks.ipynb
    └── 03_retrieval_debug.ipynb
