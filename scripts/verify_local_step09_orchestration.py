#!/usr/bin/env python3
"""Run a minimal end-to-end local verification for step 09 front-half orchestration."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from mindwiki.application.query_decomposition_service import QueryDecompositionService
from mindwiki.application.query_expansion_service import QueryExpansionService, build_query_expansion_service
from mindwiki.application.subquery_retrieval_service import SubQueryRetrievalService

DEFAULT_SAMPLE = """---
title: Step 09 Orchestration Verification Note
---

# Step 8

Step 8 focuses on retrieval foundations, including unified retrieval interfaces,
BM25 recall, vector recall, and hybrid fusion.

# Step 9

Step 9 focuses on retrieval orchestration, including query decomposition,
step-back expansion, HyDE expansion, and sub-query level candidate merging.
"""

DEFAULT_QUERY = "分别总结 Step 8 和 Step 9 的职责"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the local step 09 front-half orchestration flow.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to run the MindWiki CLI.",
    )
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help="The orchestration verification query.",
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
        sample_path = Path(tmpdir) / "step09-orchestration-verification.md"
        sample_path.write_text(DEFAULT_SAMPLE, encoding="utf-8")

        command = [
            args.python,
            "-m",
            "mindwiki",
            "import",
            "file",
            str(sample_path),
            "--tag",
            "step09-verification",
            "--tag",
            "orchestration",
            "--source-note",
            "local step09 orchestration verification",
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

    decomposition_service = QueryDecompositionService()
    expansion_service = build_query_expansion_service()
    retrieval_service = SubQueryRetrievalService()

    decomposition = decomposition_service.decompose(args.query)
    retrieval_units = decomposition.sub_queries or (args.query,)

    sub_query_results = []
    for index, sub_query in enumerate(retrieval_units, start=1):
        expansion = expansion_service.expand(sub_query)
        sub_query_result = retrieval_service.retrieve_for_sub_query(
            sub_query_id=f"sq_{index}",
            sub_query_text=sub_query,
            expansion=expansion,
            top_k=3,
        )
        sub_query_results.append(
            {
                "sub_query_id": sub_query_result.sub_query_id,
                "sub_query_text": sub_query_result.sub_query_text,
                "base_query": sub_query_result.base_query,
                "step_back_query": sub_query_result.step_back_query,
                "hyde_query": sub_query_result.hyde_query,
                "candidate_count": len(sub_query_result.candidates),
                "top_candidate": None
                if not sub_query_result.candidates
                else {
                    "chunk_id": str(sub_query_result.candidates[0].chunk_id),
                    "document_title": sub_query_result.candidates[0].projection.document_title,
                    "hit_sources": list(sub_query_result.candidates[0].hit_sources),
                    "rank_base_bm25": sub_query_result.candidates[0].rank_base_bm25,
                    "rank_base_vector": sub_query_result.candidates[0].rank_base_vector,
                    "rank_step_back_vector": sub_query_result.candidates[0].rank_step_back_vector,
                    "rank_hyde_vector": sub_query_result.candidates[0].rank_hyde_vector,
                    "fused_rrf_score": sub_query_result.candidates[0].fused_rrf_score,
                },
            }
        )

    summary = {
        "import_exit_code": completed.returncode,
        "import_stdout": stdout,
        "import_stderr": stderr,
        "import_parsed_output": parsed_output,
        "query": args.query,
        "decomposition_mode": decomposition.decomposition_mode,
        "sub_queries": list(decomposition.sub_queries),
        "sub_query_result_count": len(sub_query_results),
        "sub_query_results": sub_query_results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if completed.returncode != 0:
        return 1
    if decomposition.decomposition_mode != "decompose":
        return 1
    if len(sub_query_results) < 2:
        return 1
    for result in sub_query_results:
        if result["candidate_count"] < 1:
            return 1
        top_candidate = result["top_candidate"]
        if top_candidate is None:
            return 1
        if top_candidate["fused_rrf_score"] is None:
            return 1
        if not top_candidate["hit_sources"]:
            return 1
        if all(rank is None for rank in (
            top_candidate["rank_base_bm25"],
            top_candidate["rank_base_vector"],
            top_candidate["rank_step_back_vector"],
            top_candidate["rank_hyde_vector"],
        )):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
