#!/usr/bin/env python3
"""Run a minimal end-to-end local retrieval verification."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from mindwiki.application.import_service import normalize_tags
from mindwiki.application.retrieval_models import RetrievalFilters, RetrievalQuery, TimeRange
from mindwiki.application.retrieval_service import RetrievalService

DEFAULT_SAMPLE = """---
title: Retrieval Verification Note
---

# Overview

BM25 retrieval should find this verification note.

## Retrieval

Retrieval filtering should respect document tags and source type.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the local BM25 retrieval flow against PostgreSQL.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to run the MindWiki CLI.",
    )
    return parser


def parse_cli_output(output: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for token in output.strip().split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        result[key] = value
    return result


def main() -> int:
    args = build_parser().parse_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        sample_path = Path(tmpdir) / "retrieval-verification.md"
        sample_path.write_text(DEFAULT_SAMPLE, encoding="utf-8")

        command = [
            args.python,
            "-m",
            "mindwiki",
            "import",
            "file",
            str(sample_path),
            "--tag",
            "verification",
            "--tag",
            "retrieval",
            "--source-note",
            "local retrieval verification",
        ]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            capture_output=True,
            text=True,
            check=False,
        )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    parsed_output = parse_cli_output(stdout)
    document_id = parsed_output.get("document_id", "")

    service = RetrievalService()
    broad_result = service.retrieve(
        RetrievalQuery(
            query="verification note",
            top_k=5,
        )
    )
    tagged_result = service.retrieve(
        RetrievalQuery(
            query="retrieval filtering",
            filters=RetrievalFilters(
                tags=normalize_tags(("verification",)),
                source_types=("markdown",),
                document_scope=(UUID(document_id),) if document_id else (),
                time_range=TimeRange(
                    start_time=datetime.now() - timedelta(days=1),
                    end_time=datetime.now() + timedelta(days=1),
                ),
            ),
            top_k=5,
        )
    )

    summary = {
        "import_exit_code": completed.returncode,
        "import_stdout": stdout,
        "import_stderr": stderr,
        "import_parsed_output": parsed_output,
        "broad_hit_count": len(broad_result.hits),
        "broad_top_hit": None
        if not broad_result.hits
        else {
            "document_id": str(broad_result.hits[0].document_id),
            "document_title": broad_result.hits[0].document_title,
            "match_sources": list(broad_result.hits[0].match_sources),
            "score": broad_result.hits[0].score,
        },
        "tagged_hit_count": len(tagged_result.hits),
        "tagged_top_hit": None
        if not tagged_result.hits
        else {
            "document_id": str(tagged_result.hits[0].document_id),
            "document_title": tagged_result.hits[0].document_title,
            "source_type": tagged_result.hits[0].source_type,
            "match_sources": list(tagged_result.hits[0].match_sources),
            "score_breakdown": tagged_result.hits[0].score_breakdown,
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if completed.returncode != 0:
        return 1
    if not broad_result.hits:
        return 1
    if not tagged_result.hits:
        return 1
    if document_id and str(tagged_result.hits[0].document_id) != document_id:
        return 1
    if tagged_result.hits[0].source_type != "markdown":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
