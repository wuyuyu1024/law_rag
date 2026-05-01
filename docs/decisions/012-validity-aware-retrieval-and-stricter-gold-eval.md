# ADR 012: Validity-Aware Retrieval and Stricter Gold Evaluation

## Context

The assignment includes both historical and current legislation. A tax assistant must not answer a question for one legal date using a different version of the law.

The previous demo preserved article and paragraph citations, but chunks did not carry an explicit validity range. The gold set also checked citation substrings, which was useful but too permissive for exact statutory queries because sibling chunks could still enter the retrieved context.

## Decision

Add validity metadata to normalized documents, chunks, retrieval requests, source references, and Qdrant payloads:

- `valid_from`
- `valid_to`
- `as_of_date`

Retrieval now scopes authorized candidates by source type, jurisdiction, and validity date before lexical, dense, hybrid, or reranking stages use those candidates. When a query includes an ISO date such as `2024-01-01`, the retrieval request carries that date through initial retrieval and corrective retries.

The evaluation schema now supports stricter optional gold fields:

- `expected_citation_paths`
- `expected_chunk_ids`
- `forbidden_chunk_ids`

Exact statutory retrieval also filters sibling paragraph/subparagraph chunks when the query asks for a specific paragraph or subparagraph. In hybrid retrieval, if exact legal evidence exists, dense-only candidates are dropped from the final exact-query context.

## Why

- Validity ranges make historical/current law handling a data constraint instead of a prompt convention.
- Keeping `as_of_date` through retries prevents a focused rewrite such as `Artikel 1:1` from losing the date constraint from the original query.
- Exact chunk checks catch a real class of legal precision errors: the final citation can look correct while the context still includes sibling provisions.
- For legal/tax retrieval, it is better to return fewer exact chunks than to carry extra sibling context that may influence generation or grading.

## Tradeoffs

- Current demo source data mostly represents one law snapshot, so validity behavior is demonstrated by metadata and regression tests rather than a full historical law corpus.
- Exact-query filtering can reduce recall for poorly structured chunks. This is acceptable because missing metadata should lead to refusal or data-fix work, not broad sibling retrieval.
- The stricter gold fields are optional so broad article or ECLI queries can remain flexible when multiple chunks are legitimate evidence.

## Consequences

- The demo can now refuse an explicitly outdated law-version query with `outdated_evidence`.
- Evaluation can fail when forbidden sibling chunks enter the context, not only when they are cited.
- Qdrant payload/index setup now includes validity fields, supporting the production path for database-level scoped retrieval.
