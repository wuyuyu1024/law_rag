# Design Decisions

This folder contains short architecture decision records (ADRs) for the most important design choices in the repository.

Do not read these first. Start with [../../README.md](../../README.md), [../../SUBMISSION.md](../../SUBMISSION.md), and [../demo-script.md](../demo-script.md). Use the ADRs only as an appendix when you want the rationale behind a specific choice.

How to use them:
- Read them before interviews so you can explain not just what was built, but why it was built that way.
- Treat each ADR as a 30-60 second answer template.
- Focus on the assignment constraint that forced the decision, the alternatives considered, and the tradeoff accepted.

Current ADRs:
- `001-schema-boundaries.md`
- `002-xml-parsing.md`
- `003-legal-chunking.md`
- `004-rbac-retrieval.md`
- `005-vector-db-and-hybrid-retrieval.md`
- `006-evidence-gating-and-refusal.md`
- `007-corrective-control-flow.md`
- `008-deterministic-evaluation-baseline.md`
- `009-deterministic-reranking-and-semantic-normalization.md`
- `010-ttft-and-scale-strategy.md`
- `011-promotion-gates-and-structured-traces.md`
- `012-validity-aware-retrieval-and-stricter-gold-eval.md`
- `013-redis-backed-semantic-cache-adapter.md`
- `014-reranker-backend-boundary.md`
