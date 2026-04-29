"""Single-sub-query rerank execution for step 9.4."""

from __future__ import annotations

from mindwiki.application.retrieval_models import (
    RerankedSubQueryCandidate,
    SubQueryResult,
    SubQueryRerankResult,
)
from mindwiki.llm.rerank_models import RerankDocument
from mindwiki.llm.rerank_service import RerankInput, RerankService, build_rerank_service


class SubQueryRerankService:
    """Execute step 9.4 rerank inside one sub-query boundary."""

    def __init__(self, rerank_service: RerankService) -> None:
        self._rerank_service = rerank_service

    def rerank_sub_query(self, sub_query_result: SubQueryResult) -> SubQueryRerankResult:
        if not sub_query_result.candidates:
            return SubQueryRerankResult(
                sub_query_id=sub_query_result.sub_query_id,
                sub_query_text=sub_query_result.sub_query_text,
                reranked_candidates=(),
            )

        documents = tuple(
            RerankDocument(
                document_id=str(candidate.chunk_id),
                text=_build_rerank_document_text(candidate.projection),
                metadata={
                    "fused_rrf_score": candidate.fused_rrf_score,
                    "hit_sources": candidate.hit_sources,
                },
            )
            for candidate in sub_query_result.candidates
        )

        response = self._rerank_service.rerank(
            RerankInput(
                query=sub_query_result.sub_query_text,
                documents=documents,
                top_n=min(5, len(documents)),
                metadata={
                    "sub_query_id": sub_query_result.sub_query_id,
                    "interface_name": "sub_query_rerank",
                },
            )
        )

        candidate_by_id = {
            str(candidate.chunk_id): candidate
            for candidate in sub_query_result.candidates
        }
        reranked_candidates: list[RerankedSubQueryCandidate] = []
        for result in response.results:
            candidate = candidate_by_id.get(result.document_id)
            if candidate is None:
                continue
            reranked_candidates.append(
                RerankedSubQueryCandidate(
                    chunk_id=candidate.chunk_id,
                    projection=candidate.projection,
                    hit_sources=candidate.hit_sources,
                    fused_rrf_score=candidate.fused_rrf_score,
                    rerank_score=result.relevance_score,
                    rerank_reason=_build_rerank_reason(result.relevance_score),
                )
            )

        return SubQueryRerankResult(
            sub_query_id=sub_query_result.sub_query_id,
            sub_query_text=sub_query_result.sub_query_text,
            reranked_candidates=tuple(reranked_candidates),
        )


def build_subquery_rerank_service() -> SubQueryRerankService | None:
    """Build the default sub-query rerank service if configuration is present."""

    rerank_service = build_rerank_service()
    if rerank_service is None:
        return None
    return SubQueryRerankService(rerank_service)


def _build_rerank_document_text(projection) -> str:
    section_title = projection.section_title or ""
    parts = [
        f"document_title: {projection.document_title}",
        f"section_title: {section_title}",
        f"chunk_text: {projection.chunk_text}",
    ]
    return "\n".join(parts)


def _build_rerank_reason(score: float) -> str:
    if score >= 0.85:
        return "The reranker judged this chunk as a strong direct match for the current sub-query."
    if score >= 0.60:
        return "The reranker judged this chunk as a relevant supporting match for the current sub-query."
    return "The reranker judged this chunk as a weaker match for the current sub-query."
