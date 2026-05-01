from __future__ import annotations

from uuid import UUID

import pytest

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


class StubDecompositionService:
    def __init__(self, decomposition: QueryDecomposition) -> None:
        self._decomposition = decomposition
        self.calls = []

    def decompose(self, question: str) -> QueryDecomposition:
        self.calls.append(question)
        return self._decomposition


class StubExpansionService:
    def __init__(self) -> None:
        self.calls = []

    def expand(self, query: str) -> QueryExpansion:
        self.calls.append(query)
        return QueryExpansion(
            query=query,
            base_query=f"{query} base",
            step_back_query=f"{query} step_back",
            hyde_query=f"{query} hyde",
        )


class StubRetrievalService:
    def __init__(self) -> None:
        self.calls = []

    def retrieve_for_sub_query(self, **kwargs) -> SubQueryResult:
        self.calls.append(kwargs)
        sub_query_id = kwargs["sub_query_id"]
        sub_query_text = kwargs["sub_query_text"]
        expansion = kwargs["expansion"]
        return SubQueryResult(
            sub_query_id=sub_query_id,
            sub_query_text=sub_query_text,
            base_query=expansion.base_query,
            step_back_query=expansion.step_back_query,
            hyde_query=expansion.hyde_query,
            candidates=(),
        )


class StubRerankService:
    def __init__(self, rerank_results: dict[str, SubQueryRerankResult]) -> None:
        self._rerank_results = rerank_results
        self.calls = []

    def rerank_sub_query(self, sub_query_result: SubQueryResult) -> SubQueryRerankResult:
        self.calls.append(sub_query_result)
        return self._rerank_results[sub_query_result.sub_query_id]


class StubContextBuilder:
    def __init__(self, result: ContextBuildResult) -> None:
        self._result = result
        self.calls = []

    def build_context(self, rerank_results: tuple[SubQueryRerankResult, ...]) -> ContextBuildResult:
        self.calls.append(rerank_results)
        return self._result


class StubCitationService:
    def __init__(self, result: CitationBuildResult) -> None:
        self._result = result
        self.calls = []

    def build_citations(self, context_result: ContextBuildResult) -> CitationBuildResult:
        self.calls.append(context_result)
        return self._result


class StubAnswerService:
    def __init__(self, result: AnswerGenerationResult) -> None:
        self._result = result
        self.calls = []

    def generate_answer(
        self,
        *,
        question: str,
        context_result: ContextBuildResult,
        citation_result: CitationBuildResult,
    ) -> AnswerGenerationResult:
        self.calls.append((question, context_result, citation_result))
        return self._result


def build_rerank_result(sub_query_id: str, sub_query_text: str) -> SubQueryRerankResult:
    candidate = RerankedSubQueryCandidate(
        chunk_id=UUID("00000000-0000-0000-0000-000000000101"),
        projection=_build_projection(),
        rerank_score=0.91,
    )
    return SubQueryRerankResult(
        sub_query_id=sub_query_id,
        sub_query_text=sub_query_text,
        reranked_candidates=(candidate,),
    )


def _build_projection():
    from mindwiki.application.retrieval_models import ChunkProjection

    return ChunkProjection(
        chunk_id=UUID("00000000-0000-0000-0000-000000000101"),
        document_id=UUID("00000000-0000-0000-0000-000000000201"),
        section_id=UUID("00000000-0000-0000-0000-000000000301"),
        document_title="Step 10 Note",
        section_title="Overview",
        chunk_text="Step 10 focuses on grounded answers.",
        source_type="markdown",
        document_type="markdown",
        location=ChunkLocation(chunk_index=1),
    )


def build_context_result() -> ContextBuildResult:
    return ContextBuildResult(
        sections=(
            ContextSubQuerySection(
                sub_query_id="sq_1",
                sub_query_text="Step 8 的职责？",
                evidence_items=(
                    ContextEvidenceItem(
                        chunk_ids=(UUID("00000000-0000-0000-0000-000000000101"),),
                        document_id=UUID("00000000-0000-0000-0000-000000000201"),
                        section_id=UUID("00000000-0000-0000-0000-000000000301"),
                        document_title="Step 10 Note",
                        section_title="Overview",
                        source_type="markdown",
                        chunk_text="Step 10 focuses on grounded answers.",
                        location=ChunkLocation(chunk_index=1),
                        rerank_score=0.91,
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
                chunk_id=UUID("00000000-0000-0000-0000-000000000101"),
                document_id=UUID("00000000-0000-0000-0000-000000000201"),
                section_id=UUID("00000000-0000-0000-0000-000000000301"),
                document_title="Step 10 Note",
                section_title="Overview",
                source_type="markdown",
                snippet="Step 10 focuses on grounded answers.",
                evidence_role="primary",
                location=ChunkLocation(chunk_index=1),
            ),
        )
    )


def test_ask_runs_full_orchestration_and_returns_unified_result() -> None:
    decomposition = QueryDecomposition(
        query="  分别总结 Step 8 和 Step 9 的职责  ",
        decomposition_mode="decompose",
        sub_queries=("Step 8 的职责？", "Step 9 的职责？"),
    )
    rerank_result_1 = build_rerank_result("sq_1", "Step 8 的职责？")
    rerank_result_2 = build_rerank_result("sq_2", "Step 9 的职责？")
    context_result = build_context_result()
    citation_result = build_citation_result()
    answer_result = AnswerGenerationResult(
        question="分别总结 Step 8 和 Step 9 的职责",
        answer="Step 8 负责检索基础，Step 9 负责检索编排。",
        sources=citation_result.citations,
        confidence="medium",
    )

    service = QAOrchestrationService(
        decomposition_service=StubDecompositionService(decomposition),
        expansion_service=StubExpansionService(),
        retrieval_service=StubRetrievalService(),
        rerank_service=StubRerankService({"sq_1": rerank_result_1, "sq_2": rerank_result_2}),
        context_builder=StubContextBuilder(context_result),
        citation_service=StubCitationService(citation_result),
        answer_service=StubAnswerService(answer_result),
    )

    result = service.ask(QARequest(question="  分别总结 Step 8 和 Step 9 的职责  ", top_k=3))

    assert result.question == "分别总结 Step 8 和 Step 9 的职责"
    assert result.decomposition.decomposition_mode == "decompose"
    assert result.decomposition.sub_queries == ("Step 8 的职责？", "Step 9 的职责？")
    assert result.rerank_results == (rerank_result_1, rerank_result_2)
    assert result.context_result == context_result
    assert result.citation_result == citation_result
    assert result.answer_result == answer_result


def test_ask_uses_whole_question_when_decomposition_returns_none() -> None:
    decomposition = QueryDecomposition(
        query="Step 10 的职责是什么",
        decomposition_mode="none",
        sub_queries=(),
    )
    rerank_result = build_rerank_result("sq_1", "Step 10 的职责是什么")
    service = QAOrchestrationService(
        decomposition_service=StubDecompositionService(decomposition),
        expansion_service=StubExpansionService(),
        retrieval_service=StubRetrievalService(),
        rerank_service=StubRerankService({"sq_1": rerank_result}),
        context_builder=StubContextBuilder(build_context_result()),
        citation_service=StubCitationService(build_citation_result()),
        answer_service=StubAnswerService(
            AnswerGenerationResult(
                question="Step 10 的职责是什么",
                answer="Step 10 负责回答生成。",
                confidence="high",
            )
        ),
    )

    result = service.ask(QARequest(question="Step 10 的职责是什么"))

    assert len(result.rerank_results) == 1
    assert result.rerank_results[0].sub_query_id == "sq_1"
    assert result.rerank_results[0].sub_query_text == "Step 10 的职责是什么"


def test_ask_rejects_empty_question() -> None:
    service = QAOrchestrationService(
        decomposition_service=StubDecompositionService(QueryDecomposition(query="")),
        expansion_service=StubExpansionService(),
        retrieval_service=StubRetrievalService(),
        rerank_service=StubRerankService({}),
        context_builder=StubContextBuilder(ContextBuildResult()),
        citation_service=StubCitationService(CitationBuildResult()),
        answer_service=StubAnswerService(AnswerGenerationResult(question="", answer="")),
    )

    with pytest.raises(ValueError, match="Question must not be empty"):
        service.ask(QARequest(question="   "))


def test_ask_rejects_non_positive_top_k() -> None:
    service = QAOrchestrationService(
        decomposition_service=StubDecompositionService(QueryDecomposition(query="q")),
        expansion_service=StubExpansionService(),
        retrieval_service=StubRetrievalService(),
        rerank_service=StubRerankService({}),
        context_builder=StubContextBuilder(ContextBuildResult()),
        citation_service=StubCitationService(CitationBuildResult()),
        answer_service=StubAnswerService(AnswerGenerationResult(question="q", answer="a")),
    )

    with pytest.raises(ValueError, match="top_k must be greater than 0"):
        service.ask(QARequest(question="Step 10", top_k=0))
