#!/usr/bin/env python3
"""Build legal-aware chunk datasets from parsed JSONL documents."""

from __future__ import annotations

import argparse
from pathlib import Path

from tax_rag.chunking.pipeline import export_chunk_sets


def main() -> int:
    parser = argparse.ArgumentParser(description="Build chunk datasets from parsed legal documents.")
    parser.add_argument("--parsed-dir", default="data/parsed", help="Directory containing parsed JSONL inputs")
    parser.add_argument("--chunks-dir", default="data/chunks", help="Directory where chunk JSONL outputs will be written")
    args = parser.parse_args()

    parsed_dir = Path(args.parsed_dir)
    chunks_dir = Path(args.chunks_dir)

    law_count, case_count, merged_count = export_chunk_sets(
        laws_path=parsed_dir / "laws.jsonl",
        cases_path=parsed_dir / "cases.jsonl",
        laws_out=chunks_dir / "laws_chunks.jsonl",
        cases_out=chunks_dir / "case_chunks.jsonl",
        merged_out=chunks_dir / "legal_chunks.jsonl",
    )

    print(f"Wrote {law_count} law chunks to {chunks_dir / 'laws_chunks.jsonl'}")
    print(f"Wrote {case_count} case chunks to {chunks_dir / 'case_chunks.jsonl'}")
    print(f"Wrote {merged_count} merged chunks to {chunks_dir / 'legal_chunks.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
