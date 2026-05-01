# Live Demo Script

Use this when presenting the repository. The goal is to show that the demo is runnable, security-aware, and honest about what remains production work.

## Before Running

Say:

> This is a local architecture demo for the tax-authority RAG assignment. It is not claiming production scale, but it implements the critical control points: legal-aware chunking, pre-retrieval RBAC, hybrid retrieval, reranking, evidence grading, refusal, semantic cache policy, and promotion evaluation.

Point to:

- [SUBMISSION.md](../SUBMISSION.md) for the module-by-module answer
- [docs/architecture.md](./architecture.md) for the system diagram
- [docs/production-delta.md](./production-delta.md) for what remains before real deployment

## Command

```bash
uv run python scripts/run_interview_demo.py --dense-index-path data/indexes/qdrant
```

If the dense index has not been built:

```bash
uv run python scripts/build_dense_index.py --recreate
```

## What The Cases Prove

1. Exact statutory citation
   - Shows legal identifiers go through a precise lexical path.
   - Expected: answered with the requested article/paragraph/subparagraph citation.

2. Semantic 30 percent ruling question
   - Shows English-like natural-language phrasing can retrieve Dutch statutory evidence.
   - Expected: answered from `Uitvoeringsbesluit loonbelasting 1965 > Artikel 10ed > Lid 1` and related statutory evidence.

3. Cache hit for repeated public semantic answer
   - Shows semantic cache behavior without caching exact legal identifiers or restricted-source answers.
   - Expected: second repeated public answer has `cache_hit=True`.

4. Unauthorized restricted-source refusal
   - Shows helpdesk cannot answer from restricted fraud-triage guidance.
   - Expected: refused with `no_authorized_source`.

5. Authorized restricted-source answer
   - Shows the same restricted source is available to an authorized `inspector` role.
   - Expected: answered with Fraud Signal Triage Playbook citations.

6. Outdated as-of-date refusal
   - Shows validity-aware retrieval/refusal behavior.
   - Expected: refused with `outdated_evidence`.

## Evaluation Gate

Run this after code or config changes:

```bash
uv run python scripts/run_eval.py --candidate-label local-demo --gate-promotion
```

What to say:

> The gold set is small, but it is intentionally targeted: exact lookup, semantic lookup, refusal, RBAC, multi-part questions, citation precision, and unauthorized retrieval failures. The gate prevents a retrieval/model change from being promoted if those safety metrics regress.

## Honest Limitations

Say these explicitly:

- The demo corpus is small and partly synthetic.
- The default embedding and reranker are deterministic local baselines.
- The cross-encoder adapter exists, but production would serve it internally with a real multilingual model.
- The repository has a TTFT and scale plan, but does not prove `< 1.5 s` at 20M+ chunks end to end.
- SSO, audit logging storage, production monitoring, and full internal corpus ingestion remain production work.
