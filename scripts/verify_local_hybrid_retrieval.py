#!/usr/bin/env python3
"""Run a minimal end-to-end local hybrid retrieval verification."""

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
title: Hybrid Retrieval Verification Note
---

# Overview

Hybrid retrieval should combine exact keyword recall and semantic recall.

## Fusion

This file is used to verify bm25, vector retrieval, and final hybrid fusion ordering.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the local hybrid retrieval flow against PostgreSQL and Milvus.",
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
        sample_path = Path(tmpdir) / "hybrid-retrieval-verification.md"
        sample_path.write_text(DEFAULT_SAMPLE, encoding="utf-8")

        command = [
            args.python,
            "-m",
            "mindwiki",
            "import",
            "file",
            str(sample_path),
            "--tag",
            "hybrid-verification",
            "--tag",
            "fusion",
            "--source-note",
            "local hybrid retrieval verification",
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
            query="exact keyword recall and semantic recall fusion",
            top_k=5,
            retrieval_mode="hybrid",
        )
    )
    filtered_result = service.retrieve(
        RetrievalQuery(
            query="hybrid retrieval fusion ordering",
            filters=RetrievalFilters(
                tags=normalize_tags(("hybrid-verification",)),
                source_types=("markdown",),
                document_scope=(UUID(document_id),) if document_id else (),
                time_range=TimeRange(
                    start_time=datetime.now() - timedelta(days=1),
                    end_time=datetime.now() + timedelta(days=1),
                ),
            ),
            top_k=5,
            retrieval_mode="hybrid",
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
            "score_breakdown": broad_result.hits[0].score_breakdown,
        },
        "filtered_hit_count": len(filtered_result.hits),
        "filtered_top_hit": None
        if not filtered_result.hits
        else {
            "document_id": str(filtered_result.hits[0].document_id),
            "document_title": filtered_result.hits[0].document_title,
            "source_type": filtered_result.hits[0].source_type,
            "match_sources": list(filtered_result.hits[0].match_sources),
            "score": filtered_result.hits[0].score,
            "score_breakdown": filtered_result.hits[0].score_breakdown,
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if completed.returncode != 0:
        return 1
    if not broad_result.hits:
        return 1
    if not filtered_result.hits:
        return 1
    if document_id and str(filtered_result.hits[0].document_id) != document_id:
        return 1
    if filtered_result.hits[0].source_type != "markdown":
        return 1
    if "final_score" not in filtered_result.hits[0].score_breakdown:
        return 1
    if "rrf_score" not in filtered_result.hits[0].score_breakdown:
        return 1
    if "vector_score" not in filtered_result.hits[0].score_breakdown:
        return 1
    if "bm25_score" not in filtered_result.hits[0].score_breakdown:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
