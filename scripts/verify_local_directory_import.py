#!/usr/bin/env python3
"""Run a minimal end-to-end local directory import verification."""

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
        description="Verify the local directory import flow against PostgreSQL.",
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


def fetch_child_jobs(connection: psycopg.Connection, batch_job_id: str) -> list[dict[str, str]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT input_path, status, COALESCE(error_message, '')
            FROM import_jobs
            WHERE parent_job_id = %s
            ORDER BY input_path
            """,
            (batch_job_id,),
        )
        return [
            {
                "input_path": row[0],
                "status": row[1],
                "error_message": row[2],
            }
            for row in cursor.fetchall()
        ]


def main() -> int:
    args = build_parser().parse_args()
    database_url = read_database_url(args.database_url)

    if not database_url:
        print("Verification failed: MINDWIKI_DATABASE_URL is not configured.")
        return 1

    with psycopg.connect(database_url) as connection:
        before_counts = fetch_counts(connection)

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        markdown_path = root / "a.md"
        pdf_path = root / "b.pdf"
        text_path = root / "c.txt"
        empty_path = root / "d.md"

        markdown_path.write_text(DEFAULT_SAMPLE, encoding="utf-8")
        pdf_path.write_text("pdf", encoding="utf-8")
        text_path.write_text("txt", encoding="utf-8")
        empty_path.write_text("", encoding="utf-8")

        common_env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}

        file_command = [
            args.python,
            "-m",
            "mindwiki",
            "import",
            "file",
            str(markdown_path),
            "--tag",
            "verification",
            "--source-note",
            "local directory verification",
        ]
        file_completed = subprocess.run(
            file_command,
            cwd=ROOT,
            env=common_env,
            capture_output=True,
            text=True,
            check=False,
        )

        dir_command = [
            args.python,
            "-m",
            "mindwiki",
            "import",
            "dir",
            str(root),
        ]
        dir_completed = subprocess.run(
            dir_command,
            cwd=ROOT,
            env=common_env,
            capture_output=True,
            text=True,
            check=False,
        )

        file_stdout = file_completed.stdout.strip()
        file_stderr = file_completed.stderr.strip()
        dir_stdout = dir_completed.stdout.strip()
        dir_stderr = dir_completed.stderr.strip()
        file_parsed_output = parse_cli_output(file_stdout)
        dir_parsed_output = parse_cli_output(dir_stdout)
        batch_job_id = dir_parsed_output.get("batch_job_id", "")

        with psycopg.connect(database_url) as connection:
            after_counts = fetch_counts(connection)
            child_jobs = fetch_child_jobs(connection, batch_job_id) if batch_job_id else []

    summary = {
        "file_import": {
            "exit_code": file_completed.returncode,
            "stdout": file_stdout,
            "stderr": file_stderr,
            "parsed_output": file_parsed_output,
        },
        "directory_import": {
            "exit_code": dir_completed.returncode,
            "stdout": dir_stdout,
            "stderr": dir_stderr,
            "parsed_output": dir_parsed_output,
            "child_jobs": child_jobs,
        },
        "before_counts": before_counts,
        "after_counts": after_counts,
        "delta_counts": {
            key: after_counts[key] - before_counts[key]
            for key in before_counts
        },
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    expected_counts = {
        "sources": 1,
        "import_jobs": 6,
        "documents": 1,
        "sections": 2,
        "chunks": 2,
    }
    expected_dir_output = {
        "supported_files": "2",
        "unsupported_files": "1",
        "empty_files": "1",
        "child_jobs": "4",
        "pending_jobs": "1",
        "skipped_jobs": "3",
        "skipped_unsupported": "1",
        "skipped_empty": "1",
        "skipped_unchanged": "1",
    }
    expected_child_jobs = [
        {"name": "a.md", "status": "skipped", "error_message": "content_unchanged"},
        {"name": "b.pdf", "status": "pending", "error_message": ""},
        {"name": "c.txt", "status": "skipped", "error_message": "unsupported_file_type"},
        {"name": "d.md", "status": "skipped", "error_message": "empty_file"},
    ]

    if file_completed.returncode != 0 or dir_completed.returncode != 0:
        return 1

    if file_parsed_output.get("persistence") != "stored":
        return 1

    if dir_parsed_output.get("job_persistence") != "stored":
        return 1

    for key, expected in expected_dir_output.items():
        if dir_parsed_output.get(key) != expected:
            return 1

    for table, expected in expected_counts.items():
        if summary["delta_counts"][table] != expected:
            return 1

    if len(child_jobs) != len(expected_child_jobs):
        return 1

    for expected, actual in zip(expected_child_jobs, child_jobs, strict=True):
        if Path(actual["input_path"]).name != expected["name"]:
            return 1
        if actual["status"] != expected["status"]:
            return 1
        if actual["error_message"] != expected["error_message"]:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
