"""Unified first-stage QA orchestration entrypoint."""

from __future__ import annotations

from mindwiki.application.answer_generation_service import (
    AnswerGenerationService,
    build_answer_generation_service,
)
from mindwiki.application.citation_payload_service import CitationPayloadService
from mindwiki.application.context_builder_service import ContextBuilderService
from mindwiki.application.query_decomposition_service import (
    QueryDecompositionService,
    build_query_decomposition_service,
)
from mindwiki.application.query_expansion_service import (
    QueryExpansionService,
    build_query_expansion_service,
)
from mindwiki.application.retrieval_models import QAOrchestrationResult, QARequest
from mindwiki.application.subquery_rerank_service import (
    SubQueryRerankService,
    build_subquery_rerank_service,
)
from mindwiki.application.subquery_retrieval_service import SubQueryRetrievalService


class QAOrchestrationService:
    """Execute the full first-stage QA flow behind one application entrypoint."""

    def __init__(
        self,
        *,
        decomposition_service: QueryDecompositionService,
        expansion_service: QueryExpansionService,
        retrieval_service: SubQueryRetrievalService,
        rerank_service: SubQueryRerankService,
        context_builder: ContextBuilderService,
        citation_service: CitationPayloadService,
        answer_service: AnswerGenerationService,
    ) -> None:
        self._decomposition_service = decomposition_service
        self._expansion_service = expansion_service
        self._retrieval_service = retrieval_service
        self._rerank_service = rerank_service
        self._context_builder = context_builder
        self._citation_service = citation_service
        self._answer_service = answer_service

    def ask(self, request: QARequest) -> QAOrchestrationResult:
        normalized_question = _normalize_question(request.question)
        if not normalized_question:
            raise ValueError("Question must not be empty.")
        if request.top_k <= 0:
            raise ValueError("top_k must be greater than 0.")

        decomposition = self._decomposition_service.decompose(normalized_question)
        retrieval_units = decomposition.sub_queries or (normalized_question,)

        rerank_results = []
        for index, sub_query in enumerate(retrieval_units, start=1):
            expansion = self._expansion_service.expand(sub_query)
            retrieval_result = self._retrieval_service.retrieve_for_sub_query(
                sub_query_id=f"sq_{index}",
                sub_query_text=sub_query,
                expansion=expansion,
                filters=request.filters,
                top_k=request.top_k,
            )
            rerank_results.append(self._rerank_service.rerank_sub_query(retrieval_result))

        context_result = self._context_builder.build_context(tuple(rerank_results))
        citation_result = self._citation_service.build_citations(context_result)
        answer_result = self._answer_service.generate_answer(
            question=normalized_question,
            context_result=context_result,
            citation_result=citation_result,
        )
        return QAOrchestrationResult(
            question=normalized_question,
            decomposition=decomposition,
            rerank_results=tuple(rerank_results),
            context_result=context_result,
            citation_result=citation_result,
            answer_result=answer_result,
        )


def build_qa_orchestration_service() -> QAOrchestrationService:
    """Build the unified first-stage QA orchestration service."""

    rerank_service = build_subquery_rerank_service()
    if rerank_service is None:
        raise RuntimeError("Rerank service is not configured.")

    return QAOrchestrationService(
        decomposition_service=build_query_decomposition_service(),
        expansion_service=build_query_expansion_service(),
        retrieval_service=SubQueryRetrievalService(),
        rerank_service=rerank_service,
        context_builder=ContextBuilderService(),
        citation_service=CitationPayloadService(),
        answer_service=build_answer_generation_service(),
    )


def _normalize_question(question: str) -> str:
    return " ".join(question.strip().split()).strip()
