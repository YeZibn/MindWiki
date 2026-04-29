"""Single-sub-query four-route retrieval and merge for step 9.3."""

from __future__ import annotations

from collections import OrderedDict

from mindwiki.application.retrieval_models import (
    BM25Candidate,
    QueryExpansion,
    RetrievalFilters,
    SubQueryCandidate,
    SubQueryResult,
    VectorCandidate,
)
from mindwiki.infrastructure.retrieval_repository import RetrievalRepository, build_retrieval_repository


SUBQUERY_RRF_K = 60
BASE_BM25_WEIGHT = 0.35
BASE_VECTOR_WEIGHT = 0.30
STEP_BACK_VECTOR_WEIGHT = 0.20
HYDE_VECTOR_WEIGHT = 0.15


class SubQueryRetrievalService:
    """Execute step 9.3 retrieval inside one sub-query boundary."""

    def __init__(self, repository: RetrievalRepository | None = None) -> None:
        self._repository = repository if repository is not None else build_retrieval_repository()

    def retrieve_for_sub_query(
        self,
        *,
        sub_query_id: str,
        sub_query_text: str,
        expansion: QueryExpansion,
        filters: RetrievalFilters | None = None,
        top_k: int = 10,
    ) -> SubQueryResult:
        if self._repository is None:
            raise RuntimeError("MINDWIKI_DATABASE_URL is not configured.")

        retrieval_filters = filters if filters is not None else RetrievalFilters()
        base_bm25_candidates = self._repository.search_bm25(
            expansion.base_query,
            retrieval_filters,
            limit=top_k,
        )
        base_vector_candidates = self._repository.search_vector(
            expansion.base_query,
            retrieval_filters,
            limit=top_k,
        )

        step_back_vector_candidates: tuple[VectorCandidate, ...] = ()
        if expansion.use_step_back:
            step_back_vector_candidates = self._repository.search_vector(
                expansion.step_back_query,
                retrieval_filters,
                limit=top_k,
            )

        hyde_vector_candidates: tuple[VectorCandidate, ...] = ()
        if expansion.use_hyde:
            hyde_vector_candidates = self._repository.search_vector(
                expansion.hyde_query,
                retrieval_filters,
                limit=top_k,
            )

        merged = merge_sub_query_candidates(
            base_bm25_candidates=base_bm25_candidates,
            base_vector_candidates=base_vector_candidates,
            step_back_vector_candidates=step_back_vector_candidates,
            hyde_vector_candidates=hyde_vector_candidates,
        )
        scored = score_sub_query_candidates(merged)
        return SubQueryResult(
            sub_query_id=sub_query_id,
            sub_query_text=sub_query_text,
            base_query=expansion.base_query,
            step_back_query=expansion.step_back_query,
            hyde_query=expansion.hyde_query,
            candidates=scored[:top_k],
        )


def merge_sub_query_candidates(
    *,
    base_bm25_candidates: tuple[BM25Candidate, ...],
    base_vector_candidates: tuple[VectorCandidate, ...],
    step_back_vector_candidates: tuple[VectorCandidate, ...],
    hyde_vector_candidates: tuple[VectorCandidate, ...],
) -> tuple[SubQueryCandidate, ...]:
    """Merge all four routes by `chunk_id` while preserving route ranks."""

    merged: OrderedDict[str, SubQueryCandidate] = OrderedDict()

    for rank, candidate in enumerate(base_vector_candidates, start=1):
        _merge_vector_candidate(
            merged,
            candidate,
            rank=rank,
            hit_source="base_vector",
            rank_field="rank_base_vector",
            score_field="base_vector_score",
        )

    for rank, candidate in enumerate(step_back_vector_candidates, start=1):
        _merge_vector_candidate(
            merged,
            candidate,
            rank=rank,
            hit_source="step_back_vector",
            rank_field="rank_step_back_vector",
            score_field="step_back_vector_score",
        )

    for rank, candidate in enumerate(hyde_vector_candidates, start=1):
        _merge_vector_candidate(
            merged,
            candidate,
            rank=rank,
            hit_source="hyde_vector",
            rank_field="rank_hyde_vector",
            score_field="hyde_vector_score",
        )

    for rank, candidate in enumerate(base_bm25_candidates, start=1):
        chunk_id = str(candidate.projection.chunk_id)
        existing = merged.get(chunk_id)
        if existing is None:
            merged[chunk_id] = SubQueryCandidate(
                chunk_id=candidate.projection.chunk_id,
                projection=candidate.projection,
                hit_sources=("base_bm25",),
                rank_base_bm25=rank,
                base_bm25_score=candidate.score,
            )
            continue

        merged[chunk_id] = SubQueryCandidate(
            chunk_id=existing.chunk_id,
            projection=existing.projection,
            hit_sources=_merge_hit_sources(existing.hit_sources, ("base_bm25",)),
            rank_base_bm25=rank,
            rank_base_vector=existing.rank_base_vector,
            rank_step_back_vector=existing.rank_step_back_vector,
            rank_hyde_vector=existing.rank_hyde_vector,
            base_bm25_score=candidate.score,
            base_vector_score=existing.base_vector_score,
            step_back_vector_score=existing.step_back_vector_score,
            hyde_vector_score=existing.hyde_vector_score,
            fused_rrf_score=existing.fused_rrf_score,
        )

    return tuple(merged.values())


def score_sub_query_candidates(
    candidates: tuple[SubQueryCandidate, ...],
) -> tuple[SubQueryCandidate, ...]:
    """Apply weighted RRF fusion inside one sub-query boundary."""

    scored = tuple(_apply_sub_query_rrf(candidate) for candidate in candidates)
    return tuple(
        sorted(
            scored,
            key=lambda candidate: (
                -(candidate.fused_rrf_score or 0.0),
                -(1 if "base_bm25" in candidate.hit_sources else 0),
                -(1 if "base_vector" in candidate.hit_sources else 0),
                -(1 if "step_back_vector" in candidate.hit_sources else 0),
                -(1 if "hyde_vector" in candidate.hit_sources else 0),
            ),
        )
    )


def _merge_vector_candidate(
    merged: OrderedDict[str, SubQueryCandidate],
    candidate: VectorCandidate,
    *,
    rank: int,
    hit_source: str,
    rank_field: str,
    score_field: str,
) -> None:
    chunk_id = str(candidate.projection.chunk_id)
    existing = merged.get(chunk_id)
    if existing is None:
        merged[chunk_id] = SubQueryCandidate(
            chunk_id=candidate.projection.chunk_id,
            projection=candidate.projection,
            hit_sources=(hit_source,),
            rank_base_vector=rank if rank_field == "rank_base_vector" else None,
            rank_step_back_vector=rank if rank_field == "rank_step_back_vector" else None,
            rank_hyde_vector=rank if rank_field == "rank_hyde_vector" else None,
            base_vector_score=candidate.score if score_field == "base_vector_score" else None,
            step_back_vector_score=candidate.score if score_field == "step_back_vector_score" else None,
            hyde_vector_score=candidate.score if score_field == "hyde_vector_score" else None,
        )
        return

    merged[chunk_id] = SubQueryCandidate(
        chunk_id=existing.chunk_id,
        projection=existing.projection,
        hit_sources=_merge_hit_sources(existing.hit_sources, (hit_source,)),
        rank_base_bm25=existing.rank_base_bm25,
        rank_base_vector=rank if rank_field == "rank_base_vector" else existing.rank_base_vector,
        rank_step_back_vector=rank if rank_field == "rank_step_back_vector" else existing.rank_step_back_vector,
        rank_hyde_vector=rank if rank_field == "rank_hyde_vector" else existing.rank_hyde_vector,
        base_bm25_score=existing.base_bm25_score,
        base_vector_score=candidate.score if score_field == "base_vector_score" else existing.base_vector_score,
        step_back_vector_score=(
            candidate.score if score_field == "step_back_vector_score" else existing.step_back_vector_score
        ),
        hyde_vector_score=candidate.score if score_field == "hyde_vector_score" else existing.hyde_vector_score,
        fused_rrf_score=existing.fused_rrf_score,
    )


def _apply_sub_query_rrf(candidate: SubQueryCandidate) -> SubQueryCandidate:
    fused_rrf_score = (
        _weighted_rrf_part(candidate.rank_base_bm25, BASE_BM25_WEIGHT)
        + _weighted_rrf_part(candidate.rank_base_vector, BASE_VECTOR_WEIGHT)
        + _weighted_rrf_part(candidate.rank_step_back_vector, STEP_BACK_VECTOR_WEIGHT)
        + _weighted_rrf_part(candidate.rank_hyde_vector, HYDE_VECTOR_WEIGHT)
    )
    return SubQueryCandidate(
        chunk_id=candidate.chunk_id,
        projection=candidate.projection,
        hit_sources=candidate.hit_sources,
        rank_base_bm25=candidate.rank_base_bm25,
        rank_base_vector=candidate.rank_base_vector,
        rank_step_back_vector=candidate.rank_step_back_vector,
        rank_hyde_vector=candidate.rank_hyde_vector,
        base_bm25_score=candidate.base_bm25_score,
        base_vector_score=candidate.base_vector_score,
        step_back_vector_score=candidate.step_back_vector_score,
        hyde_vector_score=candidate.hyde_vector_score,
        fused_rrf_score=fused_rrf_score,
    )


def _weighted_rrf_part(rank: int | None, weight: float) -> float:
    if rank is None:
        return 0.0
    return weight * (1.0 / (SUBQUERY_RRF_K + rank))


def _merge_hit_sources(
    left: tuple[str, ...],
    right: tuple[str, ...],
) -> tuple[str, ...]:
    merged: list[str] = []
    for value in (*left, *right):
        if value not in merged:
            merged.append(value)
    return tuple(merged)
