#!/usr/bin/env python3
"""Run a minimal end-to-end local verification for first-stage step 10 QA."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from mindwiki.application.answer_generation_service import build_answer_generation_service
from mindwiki.application.citation_payload_service import CitationPayloadService
from mindwiki.application.context_builder_service import ContextBuilderService
from mindwiki.application.query_decomposition_service import QueryDecompositionService
from mindwiki.application.query_expansion_service import build_query_expansion_service
from mindwiki.application.retrieval_models import (
    CitationBuildResult,
    CitationPayload,
    ChunkLocation,
    ContextBuildResult,
    ContextEvidenceItem,
    ContextSubQuerySection,
)
from mindwiki.application.subquery_rerank_service import build_subquery_rerank_service
from mindwiki.application.subquery_retrieval_service import SubQueryRetrievalService

DEFAULT_SAMPLE = """---
title: Step 10 Answer Generation Verification Note
---

# Step 8

Step 8 focuses on retrieval foundations, including unified retrieval interfaces,
BM25 recall, vector recall, hybrid fusion, and chunk-level retrieval candidates.

# Step 9

Step 9 focuses on retrieval orchestration, including query decomposition,
fixed query expansion, sub-query retrieval merge, rerank, context builder,
and citation payload construction.

# Step 10

Step 10 focuses on answer generation constraints. Answers must stay grounded in
retrieved evidence, include citations, and refuse to answer when evidence is
insufficient or conflicting.
"""

DEFAULT_QUERY = "分别总结 Step 8、Step 9 和 Step 10 的职责"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the local first-stage Step 10 QA answer generation flow.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to run the MindWiki CLI.",
    )
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help="The answer-generation verification query.",
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
        sample_path = Path(tmpdir) / "step10-answer-generation-verification.md"
        sample_path.write_text(DEFAULT_SAMPLE, encoding="utf-8")

        command = [
            args.python,
            "-m",
            "mindwiki",
            "import",
            "file",
            str(sample_path),
            "--tag",
            "step10-answer-verification",
            "--tag",
            "qa",
            "--source-note",
            "local step10 answer generation verification",
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

    try:
        decomposition = QueryDecompositionService().decompose(args.query)
        expansion_service = build_query_expansion_service()
        retrieval_service = SubQueryRetrievalService()
        rerank_service = build_subquery_rerank_service()
        if rerank_service is None:
            raise RuntimeError("Rerank service is not configured.")
        context_builder = ContextBuilderService()
        citation_service = CitationPayloadService()
        answer_service = build_answer_generation_service()

        retrieval_units = decomposition.sub_queries or (args.query,)
        rerank_results = []
        for index, sub_query in enumerate(retrieval_units, start=1):
            expansion = expansion_service.expand(sub_query)
            retrieval_result = retrieval_service.retrieve_for_sub_query(
                sub_query_id=f"sq_{index}",
                sub_query_text=sub_query,
                expansion=expansion,
                top_k=5,
            )
            rerank_results.append(rerank_service.rerank_sub_query(retrieval_result))

        context_result = context_builder.build_context(tuple(rerank_results))
        citation_result = citation_service.build_citations(context_result)
        answer_result = answer_service.generate_answer(
            question=args.query,
            context_result=context_result,
            citation_result=citation_result,
        )
        isolated_context_result, isolated_citation_result = build_isolated_answer_fixture()
        isolated_answer_result = answer_service.generate_answer(
            question="Step 10 的核心约束是什么？",
            context_result=isolated_context_result,
            citation_result=isolated_citation_result,
        )
        local_no_answer_result = answer_service.generate_answer(
            question="一个没有上下文的问题",
            context_result=ContextBuildResult(),
            citation_result=CitationBuildResult(),
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "import_exit_code": completed.returncode,
                    "import_stdout": stdout,
                    "import_stderr": stderr,
                    "import_parsed_output": parsed_output,
                    "query": args.query,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    summary = {
        "import_exit_code": completed.returncode,
        "import_stdout": stdout,
        "import_stderr": stderr,
        "import_parsed_output": parsed_output,
        "query": args.query,
        "decomposition_mode": decomposition.decomposition_mode,
        "sub_queries": list(decomposition.sub_queries),
        "context_section_count": len(context_result.sections),
        "citation_count": len(citation_result.citations),
        "answer_result": {
            "answer": answer_result.answer,
            "confidence": answer_result.confidence,
            "source_count": len(answer_result.sources),
            "source_ids": [source.citation_id for source in answer_result.sources],
        },
        "isolated_answer_result": {
            "answer": isolated_answer_result.answer,
            "confidence": isolated_answer_result.confidence,
            "source_count": len(isolated_answer_result.sources),
            "source_ids": [source.citation_id for source in isolated_answer_result.sources],
        },
        "local_no_answer_result": {
            "answer": local_no_answer_result.answer,
            "confidence": local_no_answer_result.confidence,
            "source_count": len(local_no_answer_result.sources),
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if completed.returncode != 0:
        return 1
    if decomposition.decomposition_mode != "decompose":
        return 1
    if not context_result.sections:
        return 1
    if not citation_result.citations:
        return 1
    if not answer_result.answer:
        return 1
    if answer_result.confidence not in {"high", "medium", "low"}:
        return 1
    if answer_result.sources:
        if answer_result.confidence not in {"high", "medium", "low"}:
            return 1
    elif answer_result.answer not in {
        "当前检索到的知识不足以可靠回答这个问题。",
        "当前检索到的知识存在冲突，暂时无法给出可靠结论。",
        "当前暂时无法基于现有知识给出可靠回答。",
    }:
        return 1
    if not isolated_answer_result.answer:
        return 1
    if isolated_answer_result.confidence not in {"high", "medium", "low"}:
        return 1
    if isolated_answer_result.sources:
        if isolated_answer_result.confidence not in {"high", "medium", "low"}:
            return 1
    elif isolated_answer_result.answer not in {
        "当前检索到的知识不足以可靠回答这个问题。",
        "当前检索到的知识存在冲突，暂时无法给出可靠结论。",
        "当前暂时无法基于现有知识给出可靠回答。",
    }:
        return 1
    if local_no_answer_result.answer != "当前知识库中没有检索到可用于回答该问题的相关内容。":
        return 1
    if local_no_answer_result.confidence != "low":
        return 1
    if local_no_answer_result.sources:
        return 1
    return 0


def build_isolated_answer_fixture() -> tuple[ContextBuildResult, CitationBuildResult]:
    context_result = ContextBuildResult(
        sections=(
            ContextSubQuerySection(
                sub_query_id="sq_isolated_1",
                sub_query_text="Step 10 的核心约束是什么？",
                evidence_items=(
                    ContextEvidenceItem(
                        chunk_ids=(UUID("00000000-0000-0000-0000-000000000301"),),
                        document_id=UUID("00000000-0000-0000-0000-000000000311"),
                        section_id=UUID("00000000-0000-0000-0000-000000000321"),
                        document_title="Step 10 Verification Fixture",
                        section_title="Constraints",
                        source_type="markdown",
                        chunk_text=(
                            "Step 10 requires answers to stay grounded in retrieved evidence, "
                            "include citations, and refuse to answer when evidence is insufficient."
                        ),
                        location=ChunkLocation(chunk_index=1),
                        rerank_score=0.98,
                        evidence_role="primary",
                    ),
                    ContextEvidenceItem(
                        chunk_ids=(UUID("00000000-0000-0000-0000-000000000302"),),
                        document_id=UUID("00000000-0000-0000-0000-000000000312"),
                        section_id=UUID("00000000-0000-0000-0000-000000000322"),
                        document_title="Step 10 Verification Fixture",
                        section_title="Fallback",
                        source_type="markdown",
                        chunk_text=(
                            "When evidence is conflicting, the system should avoid fabrication "
                            "and return a standardized no-answer response."
                        ),
                        location=ChunkLocation(chunk_index=2),
                        rerank_score=0.94,
                        evidence_role="supporting",
                    ),
                ),
            ),
        )
    )
    citation_result = CitationBuildResult(
        citations=(
            CitationPayload(
                citation_id="cit_iso_001",
                sub_query_id="sq_isolated_1",
                chunk_id=UUID("00000000-0000-0000-0000-000000000301"),
                document_id=UUID("00000000-0000-0000-0000-000000000311"),
                section_id=UUID("00000000-0000-0000-0000-000000000321"),
                document_title="Step 10 Verification Fixture",
                section_title="Constraints",
                source_type="markdown",
                snippet=(
                    "Step 10 requires answers to stay grounded in retrieved evidence, "
                    "include citations, and refuse to answer when evidence is insufficient."
                ),
                match_sources=("chunk_text",),
                evidence_role="primary",
                location=ChunkLocation(chunk_index=1),
            ),
            CitationPayload(
                citation_id="cit_iso_002",
                sub_query_id="sq_isolated_1",
                chunk_id=UUID("00000000-0000-0000-0000-000000000302"),
                document_id=UUID("00000000-0000-0000-0000-000000000312"),
                section_id=UUID("00000000-0000-0000-0000-000000000322"),
                document_title="Step 10 Verification Fixture",
                section_title="Fallback",
                source_type="markdown",
                snippet=(
                    "When evidence is conflicting, the system should avoid fabrication "
                    "and return a standardized no-answer response."
                ),
                match_sources=("chunk_text",),
                evidence_role="supporting",
                location=ChunkLocation(chunk_index=2),
            ),
        )
    )
    return context_result, citation_result


if __name__ == "__main__":
    raise SystemExit(main())
