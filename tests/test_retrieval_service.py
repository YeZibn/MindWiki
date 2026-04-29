from __future__ import annotations

from datetime import datetime
from uuid import UUID

from mindwiki.application.retrieval_models import (
    BM25Candidate,
    ChunkLocation,
    ChunkProjection,
    RetrievalFilters,
    RetrievalQuery,
    VectorCandidate,
)
from mindwiki.application.retrieval_service import RetrievalService


class RecordingRetrievalRepository:
    def __init__(
        self,
        bm25_candidates: tuple[BM25Candidate, ...],
        vector_candidates: tuple[VectorCandidate, ...] = (),
    ) -> None:
        self._bm25_candidates = bm25_candidates
        self._vector_candidates = vector_candidates
        self.calls: list[tuple[str, str, RetrievalFilters, int]] = []

    def search_bm25(self, query_text: str, filters: RetrievalFilters, *, limit: int = 10):
        self.calls.append(("bm25_only", query_text, filters, limit))
        return self._bm25_candidates

    def search_vector(self, query_text: str, filters: RetrievalFilters, *, limit: int = 10):
        self.calls.append(("vector_only", query_text, filters, limit))
        return self._vector_candidates


def build_candidate() -> BM25Candidate:
    return BM25Candidate(
        projection=ChunkProjection(
            chunk_id=UUID("00000000-0000-0000-0000-000000000021"),
            document_id=UUID("00000000-0000-0000-0000-000000000022"),
            section_id=UUID("00000000-0000-0000-0000-000000000023"),
            document_title="RAG Notes",
            section_title="Retrieval",
            chunk_text="BM25 handles keyword recall.",
            source_type="markdown",
            document_type="markdown",
            document_tags=("rag", "retrieval"),
            location=ChunkLocation(
                chunk_index=1,
                section_id=UUID("00000000-0000-0000-0000-000000000023"),
                page_number=None,
                imported_at=datetime(2026, 4, 29, 10, 0, 0),
            ),
        ),
        score=0.73,
        match_sources=("section_title", "chunk_text"),
    )


def test_retrieve_wraps_bm25_candidates_into_chunk_hits() -> None:
    repository = RecordingRetrievalRepository((build_candidate(),))
    service = RetrievalService(repository=repository)

    result = service.retrieve(
        RetrievalQuery(
            query="keyword recall",
            top_k=3,
        )
    )

    assert result.query == "keyword recall"
    assert result.retrieval_mode == "bm25_only"
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.chunk_id == UUID("00000000-0000-0000-0000-000000000021")
    assert hit.document_title == "RAG Notes"
    assert hit.source_type == "markdown"
    assert hit.match_sources == ("section_title", "chunk_text")
    assert hit.score == 0.73
    assert hit.score_breakdown == {"bm25_score": 0.73}
    assert repository.calls[0][3] == 3


def test_retrieve_passes_strong_filters_to_repository() -> None:
    repository = RecordingRetrievalRepository((build_candidate(),))
    service = RetrievalService(repository=repository)
    filters = RetrievalFilters(
        tags=("rag",),
        source_types=("markdown",),
        document_scope=(UUID("00000000-0000-0000-0000-000000000022"),),
    )

    service.retrieve(
        RetrievalQuery(
            query="retrieval",
            filters=filters,
            top_k=5,
        )
    )

    assert repository.calls == [("bm25_only", "retrieval", filters, 5)]


def test_retrieve_wraps_vector_candidates_into_chunk_hits() -> None:
    vector_candidate = VectorCandidate(
        projection=build_candidate().projection,
        score=0.91,
    )
    repository = RecordingRetrievalRepository((), (vector_candidate,))
    service = RetrievalService(repository=repository)

    result = service.retrieve(
        RetrievalQuery(
            query="semantic recall",
            top_k=2,
            retrieval_mode="vector_only",
        )
    )

    assert result.query == "semantic recall"
    assert result.retrieval_mode == "vector_only"
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.score == 0.91
    assert hit.match_sources == ("vector",)
    assert hit.score_breakdown == {"vector_score": 0.91}
    assert repository.calls == [("vector_only", "semantic recall", RetrievalFilters(), 2)]


def test_retrieve_rejects_non_bm25_modes() -> None:
    repository = RecordingRetrievalRepository((build_candidate(),))
    service = RetrievalService(repository=repository)

    try:
        service.retrieve(
            RetrievalQuery(
                query="retrieval",
                retrieval_mode="hybrid",
            )
        )
    except ValueError as exc:
        assert "Unsupported retrieval_mode" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported retrieval mode")
