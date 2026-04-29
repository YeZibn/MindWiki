"""Application service for first-stage retrieval execution."""

from __future__ import annotations

from typing import Protocol

from mindwiki.application.retrieval_models import BM25Candidate, ChunkHit, RetrievalQuery, RetrievalResult, VectorCandidate
from mindwiki.infrastructure.retrieval_repository import RetrievalRepository, build_retrieval_repository


class RetrievalService:
    """Execute first-stage retrieval requests against the configured repository."""

    def __init__(self, repository: RetrievalRepository | None = None) -> None:
        self._repository = repository if repository is not None else build_retrieval_repository()

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        if self._repository is None:
            raise RuntimeError("MINDWIKI_DATABASE_URL is not configured.")

        if query.retrieval_mode == "bm25_only":
            candidates = self._repository.search_bm25(
                query.query,
                query.filters,
                limit=query.top_k,
            )
            hits = tuple(self._candidate_to_hit(candidate) for candidate in candidates)
            return RetrievalResult(
                query=query.query,
                retrieval_mode=query.retrieval_mode,
                hits=hits,
            )

        if query.retrieval_mode == "vector_only":
            candidates = self._repository.search_vector(
                query.query,
                query.filters,
                limit=query.top_k,
            )
            hits = tuple(self._vector_candidate_to_hit(candidate) for candidate in candidates)
            return RetrievalResult(
                query=query.query,
                retrieval_mode=query.retrieval_mode,
                hits=hits,
            )

        if query.retrieval_mode != "bm25_only":
            raise ValueError(
                f"Unsupported retrieval_mode: {query.retrieval_mode}. "
                "Only bm25_only and vector_only are implemented in the current stage."
            )
        raise AssertionError("unreachable")

    @staticmethod
    def _candidate_to_hit(candidate: BM25Candidate) -> ChunkHit:
        projection = candidate.projection
        return ChunkHit(
            chunk_id=projection.chunk_id,
            document_id=projection.document_id,
            section_id=projection.section_id,
            document_title=projection.document_title,
            section_title=projection.section_title,
            chunk_text=projection.chunk_text,
            source_type=projection.source_type,
            location=projection.location,
            score=candidate.score,
            match_sources=candidate.match_sources,
            score_breakdown={"bm25_score": candidate.score},
        )

    @staticmethod
    def _vector_candidate_to_hit(candidate: VectorCandidate) -> ChunkHit:
        projection = candidate.projection
        return ChunkHit(
            chunk_id=projection.chunk_id,
            document_id=projection.document_id,
            section_id=projection.section_id,
            document_title=projection.document_title,
            section_title=projection.section_title,
            chunk_text=projection.chunk_text,
            source_type=projection.source_type,
            location=projection.location,
            score=candidate.score,
            match_sources=candidate.match_sources,
            score_breakdown={"vector_score": candidate.score},
        )
