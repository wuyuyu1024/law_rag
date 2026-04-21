#!/usr/bin/env python3
"""
Download a small Dutch legal demo corpus in a reproducible way.

The downloader is intentionally strict:
- laws must specify an explicit `version_date`
- laws are fetched directly from versioned XML endpoints
- downloaded bytes are hashed with SHA-256
- an optional lock file can be verified or written

Usage:
    uv run python scripts/download_legal_demo_data.py \
        --config configs/data_sources.sample.json \
        --out-dir data/raw \
        --lock-file configs/demo_corpus.lock.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

USER_AGENT = "Mozilla/5.0 (compatible; legal-demo-downloader/2.0; +https://example.invalid)"
DEFAULT_TIMEOUT = 30
DEFAULT_SLEEP_SECONDS = 0.4

WETTEN_XML = "https://wetten.overheid.nl/{bwb_id}/{version_date}/0/xml"
RECHTSPRAAK_CONTENT = "https://data.rechtspraak.nl/uitspraken/content?id={ecli}"


@dataclass
class ManifestRow:
    source_type: str
    identifier: str
    name: str
    status: str
    saved_path: Optional[str]
    url: str
    sha256: Optional[str]
    version_date: Optional[str] = None
    note: str = ""


@dataclass
class FetchResult:
    content: bytes
    content_type: str
    final_url: str


def fetch_bytes(url: str, timeout: int = DEFAULT_TIMEOUT) -> FetchResult:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return FetchResult(
            content=resp.read(),
            content_type=resp.headers.get("Content-Type", ""),
            final_url=resp.geturl(),
        )


def safe_name(value: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() or ch in "._-" else "_" for ch in value.strip())
    out = out.strip("_")
    return out or "item"


def guess_ext_from_content_type(content_type: str) -> str:
    content_type = content_type.split(";", 1)[0].strip().lower()
    if not content_type:
        return ""
    if content_type in {"application/xml", "text/xml"}:
        return ".xml"
    guessed = mimetypes.guess_extension(content_type)
    return guessed or ""


def write_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def build_lock_index(lock_rows: list[dict]) -> dict[tuple[str, str, str], dict]:
    index: dict[tuple[str, str, str], dict] = {}
    for row in lock_rows:
        key = (
            row["source_type"],
            row["identifier"],
            row.get("version_date") or "",
        )
        index[key] = row
    return index


def verify_against_lock(row: ManifestRow, lock_index: dict[tuple[str, str, str], dict]) -> ManifestRow:
    key = (row.source_type, row.identifier, row.version_date or "")
    expected = lock_index.get(key)
    if expected is None:
        row.status = "mismatch"
        row.note = "Entry not found in lock file"
        return row
    if row.sha256 != expected.get("sha256"):
        row.status = "mismatch"
        row.note = (
            "SHA-256 mismatch: "
            f"expected {expected.get('sha256')}, got {row.sha256}"
        )
    return row


def is_usable_law_xml(content_type: str, content: bytes) -> bool:
    low_ct = content_type.lower()
    snippet = content[:8192].decode("utf-8", errors="ignore").lower()
    return (
        "xml" in low_ct
        and "<toestand" in snippet
        and "<wettekst" in snippet
        and "<artikel" in snippet
    )


def is_usable_case_xml(content_type: str, content: bytes) -> bool:
    low_ct = content_type.lower()
    snippet = content[:8192].decode("utf-8", errors="ignore").lower()
    return (
        "xml" in low_ct
        and "<open-rechtspraak" in snippet
        and "<uitspraak" in snippet
    )


def download_law(entry: dict, out_dir: Path) -> ManifestRow:
    bwb_id = entry.get("bwb_id")
    version_date = entry.get("version_date")
    name = entry.get("name") or bwb_id or "law"

    if not bwb_id:
        return ManifestRow("law", "", name, "error", None, "", None, note="Missing bwb_id")
    if not version_date:
        return ManifestRow(
            "law",
            bwb_id,
            name,
            "error",
            None,
            "",
            None,
            note="Missing version_date; reproducible law downloads require an explicit version",
        )

    url = WETTEN_XML.format(bwb_id=bwb_id, version_date=version_date)
    try:
        result = fetch_bytes(url)
    except (HTTPError, URLError) as exc:
        return ManifestRow(
            "law",
            bwb_id,
            name,
            "error",
            None,
            url,
            None,
            version_date=version_date,
            note=f"Failed to fetch law XML: {exc}",
        )

    if not is_usable_law_xml(result.content_type, result.content):
        return ManifestRow(
            "law",
            bwb_id,
            name,
            "error",
            None,
            result.final_url,
            None,
            version_date=version_date,
            note="Fetched content is not a usable full-text law XML export",
        )

    path = out_dir / "laws" / f"{safe_name(name)}.xml"
    write_file(path, result.content)
    return ManifestRow(
        "law",
        bwb_id,
        name,
        "ok",
        str(path),
        result.final_url,
        sha256_hex(result.content),
        version_date=version_date,
        note="Downloaded version-pinned law XML",
    )


def download_case(entry: dict, out_dir: Path) -> ManifestRow:
    ecli = entry.get("ecli")
    name = entry.get("name") or ecli or "case"
    if not ecli:
        return ManifestRow("case", "", name, "error", None, "", None, note="Missing ecli")

    url = RECHTSPRAAK_CONTENT.format(ecli=quote(ecli, safe=""))
    try:
        result = fetch_bytes(url)
    except (HTTPError, URLError) as exc:
        return ManifestRow(
            "case",
            ecli,
            name,
            "error",
            None,
            url,
            None,
            note=f"Failed to fetch case XML: {exc}",
        )

    if not is_usable_case_xml(result.content_type, result.content):
        return ManifestRow(
            "case",
            ecli,
            name,
            "error",
            None,
            result.final_url,
            None,
            note="Fetched content is not a usable Rechtspraak XML export",
        )

    ext = guess_ext_from_content_type(result.content_type) or ".xml"
    path = out_dir / "cases" / f"{safe_name(ecli)}{ext}"
    write_file(path, result.content)
    return ManifestRow(
        "case",
        ecli,
        name,
        "ok",
        str(path),
        result.final_url,
        sha256_hex(result.content),
        note="Downloaded exact ECLI XML",
    )


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a reproducible Dutch legal demo corpus.")
    parser.add_argument(
        "--config",
        default="configs/data_sources.sample.json",
        help="Path to JSON config file",
    )
    parser.add_argument(
        "--out-dir",
        default="data/raw",
        help="Directory where raw files will be stored",
    )
    parser.add_argument(
        "--lock-file",
        default="configs/demo_corpus.lock.json",
        help="Path to a tracked lock file used for verification or writing",
    )
    parser.add_argument(
        "--write-lock",
        action="store_true",
        help="Write the lock file from current downloads instead of only verifying it",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help="Delay between requests",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    out_dir = Path(args.out_dir)
    lock_path = Path(args.lock_file)

    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        return 2

    config = load_json(config_path)
    if not isinstance(config, dict):
        print("Config must be a JSON object", file=sys.stderr)
        return 2

    lock_index: dict[tuple[str, str, str], dict] = {}
    if lock_path.exists() and not args.write_lock:
        lock_rows = load_json(lock_path)
        if not isinstance(lock_rows, list):
            print("Lock file must be a JSON list", file=sys.stderr)
            return 2
        lock_index = build_lock_index(lock_rows)

    rows: list[ManifestRow] = []
    exit_code = 0

    for entry in config.get("laws", []):
        row = download_law(entry, out_dir)
        if lock_index and row.status == "ok":
            row = verify_against_lock(row, lock_index)
        rows.append(row)
        print(f"[law]  {row.identifier or row.name}: {row.status} -> {row.saved_path or '-'}")
        if row.status not in {"ok"}:
            exit_code = 1
        time.sleep(args.sleep)

    for entry in config.get("cases", []):
        row = download_case(entry, out_dir)
        if lock_index and row.status == "ok":
            row = verify_against_lock(row, lock_index)
        rows.append(row)
        print(f"[case] {row.identifier or row.name}: {row.status} -> {row.saved_path or '-'}")
        if row.status not in {"ok"}:
            exit_code = 1
        time.sleep(args.sleep)

    manifest_path = out_dir / "manifest.json"
    write_json(manifest_path, [asdict(row) for row in rows])
    print(f"\nManifest written to: {manifest_path}")

    if args.write_lock:
        if any(row.status != "ok" for row in rows):
            print("Refusing to write lock file because not all downloads succeeded", file=sys.stderr)
            return 1
        lock_payload = [
            {
                "source_type": row.source_type,
                "identifier": row.identifier,
                "name": row.name,
                "version_date": row.version_date,
                "saved_path": row.saved_path,
                "url": row.url,
                "sha256": row.sha256,
            }
            for row in rows
        ]
        write_json(lock_path, lock_payload)
        print(f"Lock file written to: {lock_path}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
