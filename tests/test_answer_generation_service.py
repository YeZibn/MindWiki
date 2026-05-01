from __future__ import annotations

from uuid import UUID

import pytest

from mindwiki.application.answer_generation_service import AnswerGenerationService
from mindwiki.application.retrieval_models import (
    AnswerGenerationResult,
    ChunkLocation,
    CitationBuildResult,
    CitationPayload,
    ContextBuildResult,
    ContextEvidenceItem,
    ContextSubQuerySection,
)
from mindwiki.llm.models import LLMError, LLMResponse, LLMValidation, ResponseTiming


class StubLLMService:
    def __init__(self, response: LLMResponse) -> None:
        self._response = response
        self.calls = []

    def generate_text(self, payload):
        self.calls.append(payload)
        return self._response


def build_context_result() -> ContextBuildResult:
    return ContextBuildResult(
        sections=(
            ContextSubQuerySection(
                sub_query_id="sq_1",
                sub_query_text="Step 10 的目标是什么",
                evidence_items=(
                    ContextEvidenceItem(
                        chunk_ids=(UUID("00000000-0000-0000-0000-000000000001"),),
                        document_id=UUID("00000000-0000-0000-0000-000000000011"),
                        section_id=UUID("00000000-0000-0000-0000-000000000021"),
                        document_title="Roadmap",
                        section_title="Step 10",
                        source_type="markdown",
                        chunk_text="Step 10 focuses on answer generation and answer constraints.",
                        location=ChunkLocation(chunk_index=1),
                        rerank_score=0.93,
                        evidence_role="primary",
                    ),
                ),
            ),
        )
    )


def build_citation_result() -> CitationBuildResult:
    return CitationBuildResult(
        citations=(
            CitationPayload(
                citation_id="cit_001",
                sub_query_id="sq_1",
                chunk_id=UUID("00000000-0000-0000-0000-000000000001"),
                document_id=UUID("00000000-0000-0000-0000-000000000011"),
                section_id=UUID("00000000-0000-0000-0000-000000000021"),
                document_title="Roadmap",
                section_title="Step 10",
                source_type="markdown",
                snippet="Step 10 focuses on answer generation and answer constraints.",
                match_sources=("chunk_text",),
                evidence_role="primary",
                location=ChunkLocation(chunk_index=1),
            ),
            CitationPayload(
                citation_id="cit_002",
                sub_query_id="sq_1",
                chunk_id=UUID("00000000-0000-0000-0000-000000000002"),
                document_id=UUID("00000000-0000-0000-0000-000000000012"),
                section_id=UUID("00000000-0000-0000-0000-000000000022"),
                document_title="Notes",
                section_title="Constraints",
                source_type="markdown",
                snippet="Answers must stay grounded in retrieved evidence.",
                match_sources=("chunk_text",),
                evidence_role="supporting",
                location=ChunkLocation(chunk_index=2),
            ),
        )
    )


def build_success_response(parsed_output: dict) -> LLMResponse:
    return LLMResponse(
        request_id="req_answer_001",
        model="gpt-5.4",
        output_text="ignored in stub",
        status="success",
        parsed_output=parsed_output,
        validation=LLMValidation(final_status="accepted"),
        timing=ResponseTiming(latency_ms=8),
    )


def test_generate_answer_returns_structured_result_with_canonical_sources() -> None:
    llm_service = StubLLMService(
        build_success_response(
            {
                "answer": "Step 10 的目标是让系统产出可靠、可引用的回答。",
                "sources": [
                    {"citation_id": "cit_001"},
                    {"citation_id": "cit_002"},
                    {"citation_id": "cit_001"},
                ],
                "confidence": "medium",
            }
        )
    )
    service = AnswerGenerationService(llm_service)

    result = service.generate_answer(
        question="Step 10 的目标是什么？",
        context_result=build_context_result(),
        citation_result=build_citation_result(),
    )

    assert result == AnswerGenerationResult(
        question="Step 10 的目标是什么？",
        answer="Step 10 的目标是让系统产出可靠、可引用的回答。",
        sources=build_citation_result().citations,
        confidence="medium",
    )
    assert len(llm_service.calls) == 1
    payload = llm_service.calls[0]
    assert payload.task_type == "rag_answer"
    assert payload.response_format is not None
    assert payload.response_format["json_schema"]["name"] == "rag_answer"
    assert payload.metadata["interface_name"] == "answer_generation"


def test_generate_answer_returns_local_no_answer_when_context_is_empty() -> None:
    llm_service = StubLLMService(build_success_response({}))
    service = AnswerGenerationService(llm_service)

    result = service.generate_answer(
        question="无法回答的问题",
        context_result=ContextBuildResult(),
        citation_result=CitationBuildResult(),
    )

    assert result.answer == "当前知识库中没有检索到可用于回答该问题的相关内容。"
    assert result.sources == ()
    assert result.confidence == "low"
    assert llm_service.calls == []


def test_generate_answer_returns_local_no_answer_when_citations_are_empty() -> None:
    llm_service = StubLLMService(build_success_response({}))
    service = AnswerGenerationService(llm_service)

    result = service.generate_answer(
        question="证据不足的问题",
        context_result=build_context_result(),
        citation_result=CitationBuildResult(),
    )

    assert result.answer == "当前检索到的知识不足以可靠回答这个问题。"
    assert result.sources == ()
    assert result.confidence == "low"
    assert llm_service.calls == []


def test_generate_answer_downgrades_invalid_confidence_to_no_answer() -> None:
    llm_service = StubLLMService(
        build_success_response(
            {
                "answer": "回答内容",
                "sources": [{"citation_id": "cit_001"}],
                "confidence": "certain",
            }
        )
    )
    service = AnswerGenerationService(llm_service)

    result = service.generate_answer(
        question="Step 10 的目标是什么？",
        context_result=build_context_result(),
        citation_result=build_citation_result(),
    )

    assert result.answer == "当前暂时无法基于现有知识给出可靠回答。"
    assert result.sources == ()
    assert result.confidence == "low"


def test_generate_answer_downgrades_unknown_citation_id_to_no_answer() -> None:
    llm_service = StubLLMService(
        build_success_response(
            {
                "answer": "回答内容",
                "sources": [{"citation_id": "cit_999"}],
                "confidence": "low",
            }
        )
    )
    service = AnswerGenerationService(llm_service)

    result = service.generate_answer(
        question="Step 10 的目标是什么？",
        context_result=build_context_result(),
        citation_result=build_citation_result(),
    )

    assert result.answer == "当前暂时无法基于现有知识给出可靠回答。"
    assert result.sources == ()
    assert result.confidence == "low"


def test_generate_answer_accepts_model_judged_insufficient_evidence_no_answer() -> None:
    llm_service = StubLLMService(
        build_success_response(
            {
                "answer": "当前检索到的知识不足以可靠回答这个问题。",
                "sources": [],
                "confidence": "low",
            }
        )
    )
    service = AnswerGenerationService(llm_service)

    result = service.generate_answer(
        question="证据不足的问题",
        context_result=build_context_result(),
        citation_result=build_citation_result(),
    )

    assert result.answer == "当前检索到的知识不足以可靠回答这个问题。"
    assert result.sources == ()
    assert result.confidence == "low"


def test_generate_answer_accepts_model_judged_conflicting_evidence_no_answer() -> None:
    llm_service = StubLLMService(
        build_success_response(
            {
                "answer": "当前检索到的知识存在冲突，暂时无法给出可靠结论。",
                "sources": [],
                "confidence": "low",
            }
        )
    )
    service = AnswerGenerationService(llm_service)

    result = service.generate_answer(
        question="冲突证据的问题",
        context_result=build_context_result(),
        citation_result=build_citation_result(),
    )

    assert result.answer == "当前检索到的知识存在冲突，暂时无法给出可靠结论。"
    assert result.sources == ()
    assert result.confidence == "low"


def test_generate_answer_downgrades_generation_failure_to_no_answer() -> None:
    llm_service = StubLLMService(
        LLMResponse(
            request_id="req_answer_002",
            model="gpt-5.4",
            output_text="",
            status="failed",
            error=LLMError(
                error_type="provider_error",
                retryable=False,
                fallback_allowed=False,
                message="boom",
            ),
        )
    )
    service = AnswerGenerationService(llm_service)

    result = service.generate_answer(
        question="生成失败的问题",
        context_result=build_context_result(),
        citation_result=build_citation_result(),
    )

    assert result.answer == "当前暂时无法基于现有知识给出可靠回答。"
    assert result.sources == ()
    assert result.confidence == "low"
