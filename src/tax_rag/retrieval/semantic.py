"""Shared legal-semantic normalization for dense retrieval and reranking."""

from __future__ import annotations

import re
from collections import defaultdict

_TOKEN_PATTERN = re.compile(r"[a-z0-9%:.+-]+", re.IGNORECASE)
_WHITESPACE_PATTERN = re.compile(r"\s+")

_STOPWORDS = {
    "a",
    "an",
    "and",
    "another",
    "be",
    "can",
    "de",
    "deze",
    "does",
    "een",
    "en",
    "for",
    "het",
    "hoe",
    "how",
    "if",
    "in",
    "is",
    "kan",
    "met",
    "naar",
    "of",
    "on",
    "or",
    "the",
    "to",
    "van",
    "wat",
    "what",
    "when",
    "werkt",
}

_CONCEPT_PATTERNS: dict[str, tuple[str, ...]] = {
    "concept:thirty_percent_ruling": (
        "30% ruling",
        "30 percent ruling",
        "30%-regeling",
        "30% regeling",
        "bewijsregel",
        "extraterritoriale",
    ),
    "concept:employee": (
        "employee",
        "employees",
        "werknemer",
        "werknemers",
        "ingekomen werknemer",
    ),
    "concept:employer": (
        "employer",
        "employers",
        "werkgever",
        "werkgevers",
        "inhoudingsplichtige",
        "inhoudingsplichtigen",
    ),
    "concept:employment_change": (
        "change employer",
        "change employers",
        "change jobs",
        "change job",
        "another employer",
        "new employer",
        "other employer",
        "switch employer",
        "switch jobs",
        "different employer",
        "andere inhoudingsplichtige",
        "nieuwe inhoudingsplichtige",
        "wisseling van inhoudingsplichtige",
        "voortgezette toepassing",
        "resterende looptijd",
    ),
    "concept:study_stage": (
        "study",
        "studied",
        "student",
        "opleiding",
        "studie",
        "stage",
        "internship",
    ),
    "concept:eligibility": (
        "qualify",
        "qualified",
        "eligible",
        "eligibility",
        "toepassing",
        "aangemerkt",
        "in aanmerking",
    ),
    "concept:netherlands": (
        "netherlands",
        "dutch",
        "nederland",
        "nederlandse",
        "nederlands",
        "nl",
    ),
}

_CONCEPT_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "concept:thirty_percent_ruling": (
        "30_percent_ruling",
        "bewijsregel",
        "extraterritoriale",
        "regeling",
    ),
    "concept:employee": ("werknemer", "employee", "ingekomen_werknemer"),
    "concept:employer": ("werkgever", "employer", "inhoudingsplichtige"),
    "concept:employment_change": (
        "switch_employer",
        "change_jobs",
        "new_employer",
        "andere_inhoudingsplichtige",
        "nieuwe_inhoudingsplichtige",
        "resterende_looptijd",
    ),
    "concept:study_stage": ("study", "opleiding", "stage", "internship"),
    "concept:eligibility": ("eligibility", "toepassing", "aangemerkt"),
    "concept:netherlands": ("netherlands", "nederland", "dutch"),
}


def normalize_text(value: str) -> str:
    return _WHITESPACE_PATTERN.sub(" ", value.lower()).strip()


def tokenize(value: str) -> tuple[str, ...]:
    return tuple(token.lower() for token in _TOKEN_PATTERN.findall(value))


def semantic_features(value: str) -> dict[str, float]:
    normalized = normalize_text(value)
    features: dict[str, float] = defaultdict(float)

    for token in tokenize(normalized):
        if token in _STOPWORDS:
            continue
        features[token] += 1.0

    for concept, patterns in _CONCEPT_PATTERNS.items():
        if any(pattern in normalized for pattern in patterns):
            features[concept] += 2.8
            for alias in _CONCEPT_EXPANSIONS[concept]:
                features[alias] += 1.4

    return dict(features)


def semantic_term_set(value: str) -> frozenset[str]:
    return frozenset(semantic_features(value))
