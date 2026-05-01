"""Load synthetic internal-policy and e-learning fixtures for the demo corpus."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from tax_rag.ingestion.normalizer import (
    normalize_e_learning_fixture,
    normalize_policy_fixture,
)
from tax_rag.schemas import NormalizedDocument


def _load_fixture_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _common_metadata(payload: dict[str, Any]) -> dict[str, object]:
    return {
        "fixture_id": payload["doc_id"],
        "simulated_source": True,
        "synthetic_fixture": True,
        **payload.get("metadata", {}),
    }


def parse_policy_fixture(path: str | Path) -> NormalizedDocument:
    fixture_path = Path(path)
    payload = _load_fixture_payload(fixture_path)
    return normalize_policy_fixture(
        doc_id=payload["doc_id"],
        title=payload["title"],
        text=payload["text"],
        source_path=str(fixture_path),
        security_classification=payload.get("security_classification", "internal"),
        allowed_roles=tuple(payload.get("allowed_roles", ("inspector", "legal_counsel"))),
        valid_from=payload.get("valid_from"),
        valid_to=payload.get("valid_to"),
        metadata=_common_metadata(payload),
    )


def parse_e_learning_fixture(path: str | Path) -> NormalizedDocument:
    fixture_path = Path(path)
    payload = _load_fixture_payload(fixture_path)
    return normalize_e_learning_fixture(
        doc_id=payload["doc_id"],
        title=payload["title"],
        text=payload["text"],
        source_path=str(fixture_path),
        allowed_roles=tuple(payload.get("allowed_roles", ("helpdesk", "inspector", "legal_counsel"))),
        valid_from=payload.get("valid_from"),
        valid_to=payload.get("valid_to"),
        metadata=_common_metadata(payload),
    )


def iter_policy_documents(raw_dir: str | Path) -> Iterator[NormalizedDocument]:
    directory = Path(raw_dir)
    for path in sorted(directory.glob("*.json")):
        yield parse_policy_fixture(path)


def iter_e_learning_documents(raw_dir: str | Path) -> Iterator[NormalizedDocument]:
    directory = Path(raw_dir)
    for path in sorted(directory.glob("*.json")):
        yield parse_e_learning_fixture(path)
