#!/usr/bin/env python3
"""Run a minimal end-to-end local verification for full step 09 orchestration."""

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

from mindwiki.application.citation_payload_service import CitationPayloadService
from mindwiki.application.context_builder_service import ContextBuilderService
from mindwiki.application.query_decomposition_service import QueryDecompositionService
from mindwiki.application.query_expansion_service import build_query_expansion_service
from mindwiki.application.subquery_rerank_service import build_subquery_rerank_service
from mindwiki.application.subquery_retrieval_service import SubQueryRetrievalService

DEFAULT_SAMPLE = """---
title: Step 09 Full Orchestration Verification Note
---

# Step 8

Step 8 focuses on retrieval foundations, including unified retrieval interfaces,
BM25 recall, vector recall, and hybrid fusion.

## Step 8 Details

Step 8 also covers indexing, chunk retrieval candidates, and retrieval score fusion.

# Step 9

Step 9 focuses on retrieval orchestration, including query decomposition,
step-back expansion, HyDE expansion, sub-query level rerank, context builder,
and citation payload construction.
"""

DEFAULT_QUERY = "分别总结 Step 8 和 Step 9 的职责"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the local full step 09 orchestration flow.",
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
        sample_path = Path(tmpdir) / "step09-full-orchestration-verification.md"
        sample_path.write_text(DEFAULT_SAMPLE, encoding="utf-8")

        command = [
            args.python,
            "-m",
            "mindwiki",
            "import",
            "file",
            str(sample_path),
            "--tag",
            "step09-full-verification",
            "--tag",
            "orchestration",
            "--source-note",
            "local step09 full orchestration verification",
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
    rerank_service = build_subquery_rerank_service()
    if rerank_service is None:
        raise RuntimeError("Rerank service is not configured.")
    context_builder = ContextBuilderService()
    citation_service = CitationPayloadService()

    decomposition = decomposition_service.decompose(args.query)
    retrieval_units = decomposition.sub_queries or (args.query,)

    rerank_results = []
    sub_query_results = []
    for index, sub_query in enumerate(retrieval_units, start=1):
        expansion = expansion_service.expand(sub_query)
        sub_query_result = retrieval_service.retrieve_for_sub_query(
            sub_query_id=f"sq_{index}",
            sub_query_text=sub_query,
            expansion=expansion,
            top_k=5,
        )
        rerank_result = rerank_service.rerank_sub_query(sub_query_result)
        sub_query_results.append(sub_query_result)
        rerank_results.append(rerank_result)

    context_result = context_builder.build_context(tuple(rerank_results))
    citation_result = citation_service.build_citations(context_result)

    summary = {
        "import_exit_code": completed.returncode,
        "import_stdout": stdout,
        "import_stderr": stderr,
        "import_parsed_output": parsed_output,
        "query": args.query,
        "decomposition_mode": decomposition.decomposition_mode,
        "sub_queries": list(decomposition.sub_queries),
        "sub_query_result_count": len(sub_query_results),
        "rerank_result_count": len(rerank_results),
        "context_section_count": len(context_result.sections),
        "citation_count": len(citation_result.citations),
        "rerank_results": [
            {
                "sub_query_id": result.sub_query_id,
                "sub_query_text": result.sub_query_text,
                "reranked_count": len(result.reranked_candidates),
                "top_reranked_candidate": None
                if not result.reranked_candidates
                else {
                    "chunk_id": str(result.reranked_candidates[0].chunk_id),
                    "document_title": result.reranked_candidates[0].projection.document_title,
                    "rerank_score": result.reranked_candidates[0].rerank_score,
                    "rerank_reason": result.reranked_candidates[0].rerank_reason,
                },
            }
            for result in rerank_results
        ],
        "context_sections": [
            {
                "sub_query_id": section.sub_query_id,
                "evidence_count": len(section.evidence_items),
                "evidence_items": [
                    {
                        "chunk_ids": [str(chunk_id) for chunk_id in item.chunk_ids],
                        "document_title": item.document_title,
                        "evidence_role": item.evidence_role,
                        "rerank_score": item.rerank_score,
                    }
                    for item in section.evidence_items
                ],
            }
            for section in context_result.sections
        ],
        "citations": [
            {
                "citation_id": citation.citation_id,
                "sub_query_id": citation.sub_query_id,
                "document_title": citation.document_title,
                "evidence_role": citation.evidence_role,
                "snippet": citation.snippet,
            }
            for citation in citation_result.citations
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if completed.returncode != 0:
        return 1
    if decomposition.decomposition_mode != "decompose":
        return 1
    if len(rerank_results) < 2:
        return 1
    if len(context_result.sections) != len(rerank_results):
        return 1
    if not citation_result.citations:
        return 1
    for result in rerank_results:
        if not result.reranked_candidates:
            return 1
        if result.reranked_candidates[0].rerank_score <= 0:
            return 1
    for section in context_result.sections:
        if not section.evidence_items:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
