"""Inspectable query transformation helpers for agent control flow."""

from __future__ import annotations

import re

from tax_rag.schemas import QueryTransformPlan, QueryTransformStrategy

_ECLI_PATTERN = re.compile(r"\bECLI:[A-Z]{2}:[A-Z0-9]+:\d{4}:[A-Z0-9]+\b", re.IGNORECASE)
_ARTICLE_PATTERN = re.compile(
    r"\b(?:artikel|article|art\.?)\s+[0-9]+[a-z]*(?:[.:][0-9]+[a-z]*)*(?:\s+lid\s+[0-9]+)?(?:\s+onderdeel\s+[a-z])?\b",
    re.IGNORECASE,
)
_MULTI_PART_SPLIT_PATTERN = re.compile(r"\s*(?:;|\?|(?:\s+(?:and|en)\s+))\s*", re.IGNORECASE)
_STATUTORY_REWRITE_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"\b(?:duration|looptijd|term).*\b(?:reduc|verminder|earlier|previous|prior|eerder).*\b(?:work|residence|verblijf|tewerkstelling|netherlands|nederland)",
            re.IGNORECASE,
        ),
        "Artikel 10ef lid 1",
    ),
    (
        re.compile(
            r"\b(?:definition|define|meaning|what is).*\b(?:incoming employee|ingekomen werknemer)\b",
            re.IGNORECASE,
        ),
        "Artikel 10e lid 2 onderdeel b",
    ),
    (
        re.compile(
            r"\b(?:duration|looptijd|how long|maximum).*\b(?:30%|30 percent|30%-regeling|proof rule|evidence rule|bewijsregel)\b",
            re.IGNORECASE,
        ),
        "Artikel 10ec lid 1",
    ),
)


def _normalize_query(value: str) -> str:
    return " ".join(value.split())


def _candidate_clauses(query: str) -> tuple[str, ...]:
    clauses = tuple(
        clause.strip(" .")
        for clause in _MULTI_PART_SPLIT_PATTERN.split(query)
        if clause and len(clause.strip()) >= 12
    )
    return tuple(dict.fromkeys(clauses))


def _identifier_queries(query: str) -> tuple[str, ...]:
    identifiers: list[str] = []
    for pattern in (_ECLI_PATTERN, _ARTICLE_PATTERN):
        for match in pattern.finditer(query):
            identifiers.append(_normalize_query(match.group(0)))
    return tuple(dict.fromkeys(identifiers))


def _statutory_rewrite_queries(query: str) -> tuple[str, ...]:
    return tuple(rewrite for pattern, rewrite in _STATUTORY_REWRITE_RULES if pattern.search(query))


def transform_query(query: str) -> QueryTransformPlan:
    normalized_query = _normalize_query(query)
    clauses = _candidate_clauses(normalized_query)
    if len(clauses) >= 2:
        return QueryTransformPlan(
            original_query=normalized_query,
            strategy=QueryTransformStrategy.DECOMPOSITION,
            transformed_queries=clauses,
            rationale="Split a multi-part query into smaller retrievable sub-questions.",
            metadata={"clause_count": len(clauses)},
        )

    identifiers = _identifier_queries(normalized_query)
    focused_queries = tuple(identifier for identifier in identifiers if identifier.lower() != normalized_query.lower())
    if focused_queries:
        return QueryTransformPlan(
            original_query=normalized_query,
            strategy=QueryTransformStrategy.STRUCTURED_IDENTIFIER,
            transformed_queries=focused_queries,
            rationale="Extracted a structured legal identifier for a more precise retry.",
            metadata={"identifier_count": len(focused_queries)},
        )

    statutory_rewrites = _statutory_rewrite_queries(normalized_query)
    if statutory_rewrites:
        return QueryTransformPlan(
            original_query=normalized_query,
            strategy=QueryTransformStrategy.STRUCTURED_IDENTIFIER,
            transformed_queries=statutory_rewrites,
            rationale="Mapped a recurring 30%-ruling question to the controlling statutory citation.",
            metadata={
                "rewrite_count": len(statutory_rewrites),
                "domain": "30_percent_ruling",
                "force_initial_retrieval": True,
            },
        )

    return QueryTransformPlan(
        original_query=normalized_query,
        strategy=QueryTransformStrategy.NONE,
        rationale="No query transformation was needed.",
    )
