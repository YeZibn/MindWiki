from __future__ import annotations

import json
from uuid import UUID

from mindwiki.application.qa_orchestration_service import QAOrchestrationService
from mindwiki.application.retrieval_models import (
    AnswerGenerationResult,
    ChunkLocation,
    CitationBuildResult,
    CitationPayload,
    ContextBuildResult,
    ContextEvidenceItem,
    ContextSubQuerySection,
    QARequest,
    QueryDecomposition,
    QueryExpansion,
    RerankedSubQueryCandidate,
    SubQueryResult,
    SubQueryRerankResult,
)
from mindwiki.llm.embedding_models import EmbeddingResponse, EmbeddingVector
from mindwiki.llm.embedding_service import EmbeddingService, GenerateEmbeddingsInput
from mindwiki.llm.models import LLMResponse, LLMValidation, ResponseTiming
from mindwiki.llm.rerank_models import RerankDocument, RerankResponse, RerankResult
from mindwiki.llm.rerank_service import RerankInput, RerankService
from mindwiki.llm.service import GenerateTextInput, LLMService


class StubTextProvider:
    def generate(self, request):
        return LLMResponse(
            request_id=str(request.metadata.get("request_id", "")),
            model=request.model or "gpt-5.4",
            output_text="done",
            status="success",
            validation=LLMValidation(final_status="accepted"),
            timing=ResponseTiming(latency_ms=5),
        )


class StubRerankProvider:
    def rerank(self, request):
        return RerankResponse(
            model=request.model,
            results=(RerankResult(index=0, document_id=request.documents[0].document_id, relevance_score=0.91),),
        )


class StubEmbeddingProvider:
    def embed(self, request):
        return EmbeddingResponse(
            model=request.model,
            provider="stub",
            vectors=(EmbeddingVector(index=0, vector=(0.1, 0.2)),),
        )


class StubDecompositionService:
    def decompose(self, question: str) -> QueryDecomposition:
        return QueryDecomposition(
            query=question,
            decomposition_mode="none",
            sub_queries=(),
        )


class StubExpansionService:
    def expand(self, query: str) -> QueryExpansion:
        return QueryExpansion(
            query=query,
            base_query=query,
            step_back_query=query,
            hyde_query=query,
        )


class StubRetrievalService:
    def retrieve_for_sub_query(self, **kwargs) -> SubQueryResult:
        return SubQueryResult(
            sub_query_id=kwargs["sub_query_id"],
            sub_query_text=kwargs["sub_query_text"],
            base_query=kwargs["expansion"].base_query,
            step_back_query=kwargs["expansion"].step_back_query,
            hyde_query=kwargs["expansion"].hyde_query,
            candidates=(),
        )


class StubRerankService:
    def rerank_sub_query(self, sub_query_result: SubQueryResult) -> SubQueryRerankResult:
        return SubQueryRerankResult(
            sub_query_id=sub_query_result.sub_query_id,
            sub_query_text=sub_query_result.sub_query_text,
            reranked_candidates=(
                RerankedSubQueryCandidate(
                    chunk_id=UUID("00000000-0000-0000-0000-000000000501"),
                    projection=_build_projection(),
                    rerank_score=0.93,
                ),
            ),
        )


class StubContextBuilder:
    def build_context(self, rerank_results: tuple[SubQueryRerankResult, ...]) -> ContextBuildResult:
        return ContextBuildResult(
            sections=(
                ContextSubQuerySection(
                    sub_query_id=rerank_results[0].sub_query_id,
                    sub_query_text=rerank_results[0].sub_query_text,
                    evidence_items=(
                        ContextEvidenceItem(
                            chunk_ids=(UUID("00000000-0000-0000-0000-000000000501"),),
                            document_id=UUID("00000000-0000-0000-0000-000000000601"),
                            section_id=UUID("00000000-0000-0000-0000-000000000701"),
                            document_title="Log Test",
                            section_title="Overview",
                            source_type="markdown",
                            chunk_text="QA logging test chunk.",
                            location=ChunkLocation(chunk_index=1),
                            rerank_score=0.93,
                            evidence_role="primary",
                        ),
                    ),
                ),
            )
        )


class StubCitationService:
    def build_citations(self, context_result: ContextBuildResult) -> CitationBuildResult:
        return CitationBuildResult(
            citations=(
                CitationPayload(
                    citation_id="cit_001",
                    sub_query_id=context_result.sections[0].sub_query_id,
                    chunk_id=UUID("00000000-0000-0000-0000-000000000501"),
                    document_id=UUID("00000000-0000-0000-0000-000000000601"),
                    section_id=UUID("00000000-0000-0000-0000-000000000701"),
                    document_title="Log Test",
                    section_title="Overview",
                    source_type="markdown",
                    snippet="QA logging test chunk.",
                    evidence_role="primary",
                    location=ChunkLocation(chunk_index=1),
                ),
            )
        )


class StubAnswerService:
    def generate_answer(self, *, question: str, context_result, citation_result) -> AnswerGenerationResult:
        return AnswerGenerationResult(
            question=question,
            answer="这是一个日志测试回答。",
            sources=citation_result.citations,
            confidence="high",
        )


def _build_projection():
    from mindwiki.application.retrieval_models import ChunkProjection

    return ChunkProjection(
        chunk_id=UUID("00000000-0000-0000-0000-000000000501"),
        document_id=UUID("00000000-0000-0000-0000-000000000601"),
        section_id=UUID("00000000-0000-0000-0000-000000000701"),
        document_title="Log Test",
        section_title="Overview",
        chunk_text="QA logging test chunk.",
        source_type="markdown",
        document_type="markdown",
        location=ChunkLocation(chunk_index=1),
    )


def test_llm_service_emits_started_and_completed_log_lines(capsys) -> None:
    service = LLMService(StubTextProvider())

    response = service.generate_text(
        GenerateTextInput(
            system_prompt="Reply plainly.",
            user_prompt="Say OK.",
            metadata={"request_id": "req_llm_log"},
        )
    )

    assert response.status == "success"
    captured = capsys.readouterr()
    lines = [json.loads(line) for line in captured.out.strip().splitlines()]
    assert [line["event"] for line in lines] == [
        "llm_generate_text_started",
        "llm_generate_text_completed",
    ]
    assert all(line["request_id"] == "req_llm_log" for line in lines)


def test_rerank_service_emits_started_and_completed_log_lines(capsys) -> None:
    service = RerankService(StubRerankProvider())

    response = service.rerank(
        RerankInput(
            query="Step 10 的职责？",
            documents=(RerankDocument(document_id="chunk_1", text="text"),),
            model="rerank-model",
            metadata={"request_id": "req_rerank_log"},
        )
    )

    assert len(response.results) == 1
    captured = capsys.readouterr()
    lines = [json.loads(line) for line in captured.out.strip().splitlines()]
    assert [line["event"] for line in lines] == ["rerank_started", "rerank_completed"]
    assert all(line["request_id"] == "req_rerank_log" for line in lines)


def test_embedding_service_emits_started_and_completed_log_lines(capsys) -> None:
    service = EmbeddingService(StubEmbeddingProvider())

    response = service.generate_embeddings(
        GenerateEmbeddingsInput(
            texts=("hello",),
            model="embed-model",
            metadata={"request_id": "req_embedding_log"},
        )
    )

    assert len(response.vectors) == 1
    captured = capsys.readouterr()
    lines = [json.loads(line) for line in captured.out.strip().splitlines()]
    assert [line["event"] for line in lines] == ["embedding_started", "embedding_completed"]
    assert all(line["request_id"] == "req_embedding_log" for line in lines)


def test_qa_orchestration_service_emits_key_stage_log_lines(capsys) -> None:
    service = QAOrchestrationService(
        decomposition_service=StubDecompositionService(),
        expansion_service=StubExpansionService(),
        retrieval_service=StubRetrievalService(),
        rerank_service=StubRerankService(),
        context_builder=StubContextBuilder(),
        citation_service=StubCitationService(),
        answer_service=StubAnswerService(),
    )

    result = service.ask(QARequest(question="Step 10 的职责是什么？"))

    assert result.answer_result.answer == "这是一个日志测试回答。"
    captured = capsys.readouterr()
    lines = [json.loads(line) for line in captured.out.strip().splitlines()]
    events = [line["event"] for line in lines]
    assert events == [
        "qa_orchestration_started",
        "qa_decomposition_completed",
        "qa_sub_query_completed",
        "qa_orchestration_completed",
    ]
    request_ids = {line["request_id"] for line in lines}
    assert len(request_ids) == 1
