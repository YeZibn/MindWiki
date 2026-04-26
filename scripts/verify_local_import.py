#!/usr/bin/env python3
"""Run a minimal end-to-end local import verification."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE = """---
title: Verification Note
tags:
  - verification
---

# Overview

This is a local verification import.

## Details

The script checks CLI import, import job creation, and core table writes.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the local Markdown import flow against PostgreSQL.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to run the MindWiki CLI.",
    )
    parser.add_argument(
        "--database-url",
        default="",
        help="Optional database URL override. Defaults to MINDWIKI_DATABASE_URL or .env.",
    )
    return parser


def read_database_url(override: str) -> str:
    if override:
        return override

    env_path = ROOT / ".env"
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("MINDWIKI_DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip("'\"")

    return ""


def fetch_counts(connection: psycopg.Connection) -> dict[str, int]:
    tables = ["sources", "import_jobs", "documents", "sections", "chunks"]
    counts: dict[str, int] = {}

    with connection.cursor() as cursor:
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]

    return counts


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
    database_url = read_database_url(args.database_url)

    if not database_url:
        print("Verification failed: MINDWIKI_DATABASE_URL is not configured.")
        return 1

    with psycopg.connect(database_url) as connection:
        before_counts = fetch_counts(connection)

    with tempfile.TemporaryDirectory() as tmpdir:
        sample_path = Path(tmpdir) / "verification.md"
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
            "--source-note",
            "local verification",
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

    with psycopg.connect(database_url) as connection:
        after_counts = fetch_counts(connection)

    summary = {
        "exit_code": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "parsed_output": parsed_output,
        "before_counts": before_counts,
        "after_counts": after_counts,
        "delta_counts": {
            key: after_counts[key] - before_counts[key]
            for key in before_counts
        },
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    expected_delta = {
        "sources": 1,
        "import_jobs": 1,
        "documents": 1,
        "sections": 2,
        "chunks": 2,
    }

    if completed.returncode != 0:
        return 1

    if parsed_output.get("persistence") != "stored":
        return 1

    for table, expected in expected_delta.items():
        if summary["delta_counts"][table] != expected:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
