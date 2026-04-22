#!/usr/bin/env python3
"""Parse raw Dutch law and case XML into normalized JSONL files."""

from __future__ import annotations

import argparse
from pathlib import Path

from tax_rag.ingestion.merge_documents import merge_jsonl_files
from tax_rag.ingestion.parser_cases import iter_case_documents
from tax_rag.ingestion.parser_laws import iter_law_documents
from tax_rag.ingestion.synthetic_sources import (
    iter_e_learning_documents,
    iter_policy_documents,
)


def write_jsonl(path: Path, records: list[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"{record.to_json()}\n" for record in records),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse raw XML data into normalized JSONL files.")
    parser.add_argument("--raw-dir", default="data/raw", help="Directory containing raw source files")
    parser.add_argument("--parsed-dir", default="data/parsed", help="Directory for parsed JSONL outputs")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    parsed_dir = Path(args.parsed_dir)

    law_docs = list(iter_law_documents(raw_dir / "laws"))
    case_docs = list(iter_case_documents(raw_dir / "cases"))
    policy_docs = list(iter_policy_documents(raw_dir / "internal_policy"))
    e_learning_docs = list(iter_e_learning_documents(raw_dir / "e_learning"))

    laws_path = parsed_dir / "laws.jsonl"
    cases_path = parsed_dir / "cases.jsonl"
    policies_path = parsed_dir / "policies.jsonl"
    e_learning_path = parsed_dir / "e_learning.jsonl"
    merged_path = parsed_dir / "documents.jsonl"

    write_jsonl(laws_path, law_docs)
    write_jsonl(cases_path, case_docs)
    write_jsonl(policies_path, policy_docs)
    write_jsonl(e_learning_path, e_learning_docs)
    merged_count = merge_jsonl_files([laws_path, cases_path, policies_path, e_learning_path], merged_path)

    print(f"Wrote {len(law_docs)} law records to {laws_path}")
    print(f"Wrote {len(case_docs)} case records to {cases_path}")
    print(f"Wrote {len(policy_docs)} policy records to {policies_path}")
    print(f"Wrote {len(e_learning_docs)} e-learning records to {e_learning_path}")
    print(f"Wrote {merged_count} merged records to {merged_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
