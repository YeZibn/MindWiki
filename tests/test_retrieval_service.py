from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pytest

from mindwiki.application.retrieval_models import (
    BM25Candidate,
    ChunkLocation,
    ChunkProjection,
    HybridCandidate,
    QueryDecomposition,
    QueryExpansion,
    RetrievalFilters,
    RetrievalQuery,
    VectorCandidate,
)
from mindwiki.application.query_decomposition_service import QueryDecompositionService
from mindwiki.application.query_expansion_service import QueryExpansionService
from mindwiki.application.retrieval_service import RetrievalService, merge_hybrid_candidates, score_hybrid_candidates
from mindwiki.llm.models import LLMError, LLMResponse, LLMValidation, ResponseTiming


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


class RecordingLLMService:
    def __init__(self, response: LLMResponse) -> None:
        self._response = response
        self.calls = []

    def generate_text(self, payload):
        self.calls.append(payload)
        return self._response


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


def test_query_decomposition_defaults_to_none_for_single_topic_query() -> None:
    service = QueryDecompositionService()

    result = service.decompose("总结一下 Step 8 的设计思路")

    assert result == QueryDecomposition(
        query="总结一下 Step 8 的设计思路",
        decomposition_mode="none",
        sub_queries=(),
        reason=None,
    )


def test_query_decomposition_splits_explicit_comparison_queries() -> None:
    service = QueryDecompositionService()

    result = service.decompose("BM25 和 embedding 检索有什么区别？")

    assert result == QueryDecomposition(
        query="BM25 和 embedding 检索有什么区别？",
        decomposition_mode="decompose",
        sub_queries=(
            "BM25的职责边界或核心特点是什么？",
            "embedding 检索的职责边界或核心特点是什么？",
        ),
        reason="comparison_detected",
    )


def test_query_decomposition_splits_prefixed_multi_object_summary_queries() -> None:
    service = QueryDecompositionService()

    result = service.decompose("分别总结 Step 8 和 Step 9 的职责")

    assert result == QueryDecomposition(
        query="分别总结 Step 8 和 Step 9 的职责",
        decomposition_mode="decompose",
        sub_queries=("Step 8的职责？", "Step 9的职责？"),
        reason="multi_object_summary_detected",
    )


def test_query_decomposition_splits_multi_point_queries_when_clauses_are_independent() -> None:
    service = QueryDecompositionService()

    result = service.decompose("解释 chunk 打分的作用，并且说明 rerank 的作用")

    assert result == QueryDecomposition(
        query="解释 chunk 打分的作用，并且说明 rerank 的作用",
        decomposition_mode="decompose",
        sub_queries=("解释 chunk 打分的作用？", "说明 rerank 的作用？"),
        reason="multi_point_detected",
    )


def test_query_decomposition_keeps_pronoun_dependent_multi_point_query_whole() -> None:
    service = QueryDecompositionService()

    result = service.decompose("总结 Step 8，并说明它和 Step 9 的关系")

    assert result == QueryDecomposition(
        query="总结 Step 8，并说明它和 Step 9 的关系",
        decomposition_mode="none",
        sub_queries=(),
        reason=None,
    )


def test_query_expansion_generates_fixed_base_step_back_and_hyde_queries() -> None:
    llm_service = RecordingLLMService(
        LLMResponse(
            request_id="req_001",
            model="gpt-5.4",
            output_text='{"step_back_query":"检索召回层的职责边界是什么？","hyde_query":"检索召回层负责根据用户问题召回相关 chunk，并为后续排序与生成提供候选证据。"}',
            status="success",
            parsed_output={
                "step_back_query": "检索召回层的职责边界是什么？",
                "hyde_query": "检索召回层负责根据用户问题召回相关 chunk，并为后续排序与生成提供候选证据。",
            },
            validation=LLMValidation(final_status="accepted"),
            timing=ResponseTiming(latency_ms=5),
        )
    )
    service = QueryExpansionService(llm_service=llm_service)

    result = service.expand("为什么要给 chunk 打分？")

    assert result == QueryExpansion(
        query="为什么要给 chunk 打分？",
        base_query="为什么要给 chunk 打分？",
        step_back_query="检索召回层的职责边界是什么？",
        hyde_query="检索召回层负责根据用户问题召回相关 chunk，并为后续排序与生成提供候选证据。",
        use_step_back=True,
        use_hyde=True,
    )
    assert len(llm_service.calls) == 1
    payload = llm_service.calls[0]
    assert payload.task_type == "query_expansion"
    assert payload.response_format is not None
    assert payload.metadata["interface_name"] == "query_expansion"


def test_query_expansion_raises_when_llm_generation_fails() -> None:
    llm_service = RecordingLLMService(
        LLMResponse(
            request_id="req_002",
            model="gpt-5.4",
            output_text="",
            status="failed",
            validation=LLMValidation(final_status="repairable"),
            timing=ResponseTiming(latency_ms=5),
            error=LLMError(
                error_type="network_error",
                retryable=True,
                fallback_allowed=True,
                message="temporary",
            ),
        )
    )
    service = QueryExpansionService(llm_service=llm_service)

    with pytest.raises(RuntimeError, match="Failed to generate query expansion"):
        service.expand("为什么要给 chunk 打分？")


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


def test_retrieve_rejects_unknown_modes() -> None:
    repository = RecordingRetrievalRepository((build_candidate(),))
    service = RetrievalService(repository=repository)

    try:
        service.retrieve(
            RetrievalQuery(
                query="retrieval",
                retrieval_mode="unsupported_mode",
            )
        )
    except ValueError as exc:
        assert "Unsupported retrieval_mode" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported retrieval mode")


def test_retrieve_hybrid_merges_two_channels_and_returns_final_score() -> None:
    bm25_candidate = build_candidate()
    vector_candidate = VectorCandidate(
        projection=bm25_candidate.projection,
        score=0.91,
    )
    repository = RecordingRetrievalRepository((bm25_candidate,), (vector_candidate,))
    service = RetrievalService(repository=repository)

    result = service.retrieve(
        RetrievalQuery(
            query="hybrid retrieval",
            top_k=3,
            retrieval_mode="hybrid",
        )
    )

    assert result.query == "hybrid retrieval"
    assert result.retrieval_mode == "hybrid"
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.chunk_id == bm25_candidate.projection.chunk_id
    assert hit.score > 0
    assert hit.match_sources == ("vector", "section_title", "chunk_text")
    assert "vector_score" in hit.score_breakdown
    assert "bm25_score" in hit.score_breakdown
    assert "rrf_score" in hit.score_breakdown
    assert "normalized_rrf_score" in hit.score_breakdown
    assert "normalized_vector_score" in hit.score_breakdown
    assert "normalized_bm25_score" in hit.score_breakdown
    assert "dual_hit_bonus" in hit.score_breakdown
    assert "final_score" in hit.score_breakdown
    assert repository.calls == [
        ("bm25_only", "hybrid retrieval", RetrievalFilters(), 3),
        ("vector_only", "hybrid retrieval", RetrievalFilters(), 3),
    ]


def test_merge_hybrid_candidates_combines_dual_hit_candidates_by_chunk_id() -> None:
    projection = build_candidate().projection
    merged = merge_hybrid_candidates(
        bm25_candidates=(
            BM25Candidate(
                projection=projection,
                score=0.73,
                match_sources=("section_title", "chunk_text"),
            ),
        ),
        vector_candidates=(
            VectorCandidate(
                projection=projection,
                score=0.91,
            ),
        ),
    )

    assert merged == (
        HybridCandidate(
            chunk_id=projection.chunk_id,
            projection=projection,
            vector_hit=True,
            bm25_hit=True,
            vector_score=0.91,
            bm25_score=0.73,
            rank_vector=1,
            rank_bm25=1,
            match_sources=("vector", "section_title", "chunk_text"),
        ),
    )


def test_merge_hybrid_candidates_preserves_single_channel_hits_and_ranks() -> None:
    first_projection = build_candidate().projection
    second_projection = ChunkProjection(
        chunk_id=UUID("00000000-0000-0000-0000-000000000031"),
        document_id=UUID("00000000-0000-0000-0000-000000000032"),
        section_id=UUID("00000000-0000-0000-0000-000000000033"),
        document_title="Semantic Notes",
        section_title="Embeddings",
        chunk_text="Vector retrieval handles semantic recall.",
        source_type="markdown",
        document_type="markdown",
        document_tags=("vector",),
        location=ChunkLocation(
            chunk_index=2,
            section_id=UUID("00000000-0000-0000-0000-000000000033"),
            page_number=None,
            imported_at=datetime(2026, 4, 29, 11, 0, 0),
        ),
    )

    merged = merge_hybrid_candidates(
        bm25_candidates=(
            BM25Candidate(
                projection=second_projection,
                score=0.63,
                match_sources=("chunk_text",),
            ),
        ),
        vector_candidates=(
            VectorCandidate(
                projection=first_projection,
                score=0.91,
            ),
            VectorCandidate(
                projection=second_projection,
                score=0.88,
            ),
        ),
    )

    assert merged == (
        HybridCandidate(
            chunk_id=first_projection.chunk_id,
            projection=first_projection,
            vector_hit=True,
            bm25_hit=False,
            vector_score=0.91,
            bm25_score=None,
            rank_vector=1,
            rank_bm25=None,
            match_sources=("vector",),
        ),
        HybridCandidate(
            chunk_id=second_projection.chunk_id,
            projection=second_projection,
            vector_hit=True,
            bm25_hit=True,
            vector_score=0.88,
            bm25_score=0.63,
            rank_vector=2,
            rank_bm25=1,
            match_sources=("vector", "chunk_text"),
        ),
    )


def test_score_hybrid_candidates_applies_rrf_normalization_and_final_score() -> None:
    first_projection = build_candidate().projection
    second_projection = ChunkProjection(
        chunk_id=UUID("00000000-0000-0000-0000-000000000031"),
        document_id=UUID("00000000-0000-0000-0000-000000000032"),
        section_id=UUID("00000000-0000-0000-0000-000000000033"),
        document_title="Semantic Notes",
        section_title="Embeddings",
        chunk_text="Vector retrieval handles semantic recall.",
        source_type="markdown",
        document_type="markdown",
        document_tags=("vector",),
        location=ChunkLocation(
            chunk_index=2,
            section_id=UUID("00000000-0000-0000-0000-000000000033"),
            page_number=None,
            imported_at=datetime(2026, 4, 29, 11, 0, 0),
        ),
    )
    third_projection = ChunkProjection(
        chunk_id=UUID("00000000-0000-0000-0000-000000000041"),
        document_id=UUID("00000000-0000-0000-0000-000000000042"),
        section_id=UUID("00000000-0000-0000-0000-000000000043"),
        document_title="Keyword Notes",
        section_title="BM25",
        chunk_text="BM25 is strong at exact term recall.",
        source_type="markdown",
        document_type="markdown",
        document_tags=("bm25",),
        location=ChunkLocation(
            chunk_index=3,
            section_id=UUID("00000000-0000-0000-0000-000000000043"),
            page_number=None,
            imported_at=datetime(2026, 4, 29, 12, 0, 0),
        ),
    )

    merged = (
        HybridCandidate(
            chunk_id=first_projection.chunk_id,
            projection=first_projection,
            vector_hit=True,
            bm25_hit=True,
            vector_score=0.91,
            bm25_score=0.73,
            rank_vector=1,
            rank_bm25=2,
            match_sources=("vector", "section_title", "chunk_text"),
        ),
        HybridCandidate(
            chunk_id=second_projection.chunk_id,
            projection=second_projection,
            vector_hit=True,
            bm25_hit=False,
            vector_score=0.88,
            bm25_score=None,
            rank_vector=2,
            rank_bm25=None,
            match_sources=("vector",),
        ),
        HybridCandidate(
            chunk_id=third_projection.chunk_id,
            projection=third_projection,
            vector_hit=False,
            bm25_hit=True,
            vector_score=None,
            bm25_score=0.81,
            rank_vector=None,
            rank_bm25=1,
            match_sources=("chunk_text",),
        ),
    )

    scored = score_hybrid_candidates(merged)

    assert scored[0].chunk_id == first_projection.chunk_id
    assert scored[0].rrf_score is not None
    assert scored[0].normalized_rrf_score == 1.0
    assert scored[0].normalized_vector_score == 1.0
    assert scored[0].normalized_bm25_score == 0.0
    assert scored[0].dual_hit_bonus == 1.0
    assert scored[0].final_score == pytest.approx(0.8)

    assert scored[1].chunk_id == third_projection.chunk_id
    assert scored[1].normalized_vector_score == 0.0
    assert scored[1].normalized_bm25_score == 1.0
    assert scored[1].dual_hit_bonus == 0.0

    assert scored[2].chunk_id == second_projection.chunk_id
    assert scored[2].normalized_bm25_score == 0.0
    assert scored[2].dual_hit_bonus == 0.0


def test_score_hybrid_candidates_uses_one_when_all_values_in_a_column_are_equal() -> None:
    projection = build_candidate().projection
    merged = (
        HybridCandidate(
            chunk_id=projection.chunk_id,
            projection=projection,
            vector_hit=True,
            bm25_hit=False,
            vector_score=0.5,
            bm25_score=None,
            rank_vector=1,
            rank_bm25=None,
            match_sources=("vector",),
        ),
        HybridCandidate(
            chunk_id=UUID("00000000-0000-0000-0000-000000000099"),
            projection=ChunkProjection(
                chunk_id=UUID("00000000-0000-0000-0000-000000000099"),
                document_id=projection.document_id,
                section_id=projection.section_id,
                document_title="Another",
                section_title=projection.section_title,
                chunk_text="Another vector hit.",
                source_type="markdown",
                document_type="markdown",
                document_tags=(),
                location=projection.location,
            ),
            vector_hit=True,
            bm25_hit=False,
            vector_score=0.5,
            bm25_score=None,
            rank_vector=2,
            rank_bm25=None,
            match_sources=("vector",),
        ),
    )

    scored = score_hybrid_candidates(merged)

    assert scored[0].normalized_vector_score == 1.0
    assert scored[1].normalized_vector_score == 1.0


def test_score_hybrid_candidates_uses_tie_break_order_after_equal_final_score() -> None:
    first_projection = build_candidate().projection
    second_projection = ChunkProjection(
        chunk_id=UUID("00000000-0000-0000-0000-000000000051"),
        document_id=UUID("00000000-0000-0000-0000-000000000052"),
        section_id=UUID("00000000-0000-0000-0000-000000000053"),
        document_title="Another Note",
        section_title="Another Section",
        chunk_text="Another chunk text.",
        source_type="markdown",
        document_type="markdown",
        document_tags=(),
        location=ChunkLocation(
            chunk_index=4,
            section_id=UUID("00000000-0000-0000-0000-000000000053"),
            page_number=None,
            imported_at=datetime(2026, 4, 29, 13, 0, 0),
        ),
    )

    candidates = (
        HybridCandidate(
            chunk_id=first_projection.chunk_id,
            projection=first_projection,
            vector_hit=True,
            bm25_hit=True,
            vector_score=0.8,
            bm25_score=0.8,
            rank_vector=1,
            rank_bm25=2,
            match_sources=("vector", "chunk_text"),
            rrf_score=0.03,
            normalized_rrf_score=0.7,
            normalized_vector_score=0.5,
            normalized_bm25_score=0.5,
            dual_hit_bonus=1.0,
            final_score=0.75,
        ),
        HybridCandidate(
            chunk_id=second_projection.chunk_id,
            projection=second_projection,
            vector_hit=True,
            bm25_hit=False,
            vector_score=0.9,
            bm25_score=None,
            rank_vector=1,
            rank_bm25=None,
            match_sources=("vector",),
            rrf_score=0.02,
            normalized_rrf_score=0.9,
            normalized_vector_score=0.9,
            normalized_bm25_score=0.0,
            dual_hit_bonus=0.0,
            final_score=0.75,
        ),
    )

    scored = score_hybrid_candidates(candidates)

    assert scored[0].chunk_id == first_projection.chunk_id
    assert scored[1].chunk_id == second_projection.chunk_id
