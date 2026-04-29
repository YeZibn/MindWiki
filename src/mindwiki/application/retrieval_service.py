"""Application service for first-stage retrieval execution."""

from __future__ import annotations

from collections import OrderedDict

from mindwiki.application.retrieval_models import (
    BM25Candidate,
    ChunkHit,
    HybridCandidate,
    RetrievalQuery,
    RetrievalResult,
    VectorCandidate,
)
from mindwiki.infrastructure.retrieval_repository import RetrievalRepository, build_retrieval_repository


RRF_K = 60


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

        if query.retrieval_mode == "hybrid":
            bm25_candidates = self._repository.search_bm25(
                query.query,
                query.filters,
                limit=query.top_k,
            )
            vector_candidates = self._repository.search_vector(
                query.query,
                query.filters,
                limit=query.top_k,
            )
            merged = merge_hybrid_candidates(
                bm25_candidates=bm25_candidates,
                vector_candidates=vector_candidates,
            )
            scored = score_hybrid_candidates(merged)
            hits = tuple(self._hybrid_candidate_to_hit(candidate) for candidate in scored[: query.top_k])
            return RetrievalResult(
                query=query.query,
                retrieval_mode=query.retrieval_mode,
                hits=hits,
            )

        if query.retrieval_mode not in {"bm25_only", "vector_only", "hybrid"}:
            raise ValueError(
                f"Unsupported retrieval_mode: {query.retrieval_mode}. "
                "Only bm25_only, vector_only, and hybrid are implemented in the current stage."
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

    @staticmethod
    def _hybrid_candidate_to_hit(candidate: HybridCandidate) -> ChunkHit:
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
            score=float(candidate.final_score or 0.0),
            match_sources=candidate.match_sources,
            score_breakdown={"final_score": float(candidate.final_score or 0.0)},
        )


def merge_hybrid_candidates(
    bm25_candidates: tuple[BM25Candidate, ...],
    vector_candidates: tuple[VectorCandidate, ...],
) -> tuple[HybridCandidate, ...]:
    """Merge two candidate lists by `chunk_id` without applying fusion scoring."""

    merged: OrderedDict[str, HybridCandidate] = OrderedDict()

    for rank, candidate in enumerate(vector_candidates, start=1):
        chunk_id = str(candidate.projection.chunk_id)
        existing = merged.get(chunk_id)
        if existing is None:
            merged[chunk_id] = HybridCandidate(
                chunk_id=candidate.projection.chunk_id,
                projection=candidate.projection,
                vector_hit=True,
                vector_score=candidate.score,
                rank_vector=rank,
                match_sources=candidate.match_sources,
            )
            continue

        merged[chunk_id] = HybridCandidate(
            chunk_id=existing.chunk_id,
            projection=existing.projection,
            vector_hit=True,
            bm25_hit=existing.bm25_hit,
            vector_score=candidate.score,
            bm25_score=existing.bm25_score,
            rank_vector=rank,
            rank_bm25=existing.rank_bm25,
            match_sources=_merge_match_sources(existing.match_sources, candidate.match_sources),
        )

    for rank, candidate in enumerate(bm25_candidates, start=1):
        chunk_id = str(candidate.projection.chunk_id)
        existing = merged.get(chunk_id)
        if existing is None:
            merged[chunk_id] = HybridCandidate(
                chunk_id=candidate.projection.chunk_id,
                projection=candidate.projection,
                bm25_hit=True,
                bm25_score=candidate.score,
                rank_bm25=rank,
                match_sources=candidate.match_sources,
            )
            continue

        merged[chunk_id] = HybridCandidate(
            chunk_id=existing.chunk_id,
            projection=existing.projection,
            vector_hit=existing.vector_hit,
            bm25_hit=True,
            vector_score=existing.vector_score,
            bm25_score=candidate.score,
            rank_vector=existing.rank_vector,
            rank_bm25=rank,
            match_sources=_merge_match_sources(existing.match_sources, candidate.match_sources),
        )

    return tuple(merged.values())


def score_hybrid_candidates(
    candidates: tuple[HybridCandidate, ...],
) -> tuple[HybridCandidate, ...]:
    """Apply first-stage hybrid fusion scoring and ordering."""

    if not candidates:
        return ()

    with_rrf = tuple(_apply_rrf(candidate) for candidate in candidates)
    normalized_rrf = _normalize_candidate_field(with_rrf, "rrf_score")
    normalized_vector = _normalize_candidate_field(normalized_rrf, "vector_score")
    normalized_bm25 = _normalize_candidate_field(normalized_vector, "bm25_score")
    with_final_scores = tuple(_apply_final_score(candidate) for candidate in normalized_bm25)

    return tuple(
        sorted(
            with_final_scores,
            key=lambda candidate: (
                -(candidate.final_score or 0.0),
                -(candidate.dual_hit_bonus or 0.0),
                -(candidate.normalized_rrf_score or 0.0),
                -(candidate.normalized_vector_score or 0.0),
                -(candidate.normalized_bm25_score or 0.0),
            ),
        )
    )


def _apply_rrf(candidate: HybridCandidate) -> HybridCandidate:
    vector_rrf_part = 0.0
    if candidate.vector_hit and candidate.rank_vector is not None:
        vector_rrf_part = 1.0 / (RRF_K + candidate.rank_vector)

    bm25_rrf_part = 0.0
    if candidate.bm25_hit and candidate.rank_bm25 is not None:
        bm25_rrf_part = 1.0 / (RRF_K + candidate.rank_bm25)

    return HybridCandidate(
        chunk_id=candidate.chunk_id,
        projection=candidate.projection,
        vector_hit=candidate.vector_hit,
        bm25_hit=candidate.bm25_hit,
        vector_score=candidate.vector_score,
        bm25_score=candidate.bm25_score,
        rank_vector=candidate.rank_vector,
        rank_bm25=candidate.rank_bm25,
        match_sources=candidate.match_sources,
        rrf_score=vector_rrf_part + bm25_rrf_part,
        normalized_rrf_score=candidate.normalized_rrf_score,
        normalized_vector_score=candidate.normalized_vector_score,
        normalized_bm25_score=candidate.normalized_bm25_score,
        dual_hit_bonus=candidate.dual_hit_bonus,
        final_score=candidate.final_score,
    )


def _normalize_candidate_field(
    candidates: tuple[HybridCandidate, ...],
    field_name: str,
) -> tuple[HybridCandidate, ...]:
    hit_values: list[float] = []
    for candidate in candidates:
        if field_name == "rrf_score":
            hit_values.append(float(candidate.rrf_score or 0.0))
        elif field_name == "vector_score":
            if candidate.vector_hit and candidate.vector_score is not None:
                hit_values.append(candidate.vector_score)
        elif field_name == "bm25_score":
            if candidate.bm25_hit and candidate.bm25_score is not None:
                hit_values.append(candidate.bm25_score)
        else:
            raise ValueError(f"Unsupported normalization field: {field_name}")

    if not hit_values:
        min_value = 0.0
        max_value = 0.0
    else:
        min_value = min(hit_values)
        max_value = max(hit_values)

    normalized_candidates: list[HybridCandidate] = []
    for candidate in candidates:
        normalized_value = _normalized_value(
            candidate=candidate,
            field_name=field_name,
            min_value=min_value,
            max_value=max_value,
        )
        normalized_candidates.append(
            HybridCandidate(
                chunk_id=candidate.chunk_id,
                projection=candidate.projection,
                vector_hit=candidate.vector_hit,
                bm25_hit=candidate.bm25_hit,
                vector_score=candidate.vector_score,
                bm25_score=candidate.bm25_score,
                rank_vector=candidate.rank_vector,
                rank_bm25=candidate.rank_bm25,
                match_sources=candidate.match_sources,
                rrf_score=candidate.rrf_score,
                normalized_rrf_score=normalized_value if field_name == "rrf_score" else candidate.normalized_rrf_score,
                normalized_vector_score=normalized_value if field_name == "vector_score" else candidate.normalized_vector_score,
                normalized_bm25_score=normalized_value if field_name == "bm25_score" else candidate.normalized_bm25_score,
                dual_hit_bonus=candidate.dual_hit_bonus,
                final_score=candidate.final_score,
            )
        )
    return tuple(normalized_candidates)


def _normalized_value(
    *,
    candidate: HybridCandidate,
    field_name: str,
    min_value: float,
    max_value: float,
) -> float:
    if field_name == "rrf_score":
        raw_value = float(candidate.rrf_score or 0.0)
        if max_value == min_value:
            return 1.0
        return (raw_value - min_value) / (max_value - min_value)

    if field_name == "vector_score":
        if not candidate.vector_hit or candidate.vector_score is None:
            return 0.0
        if max_value == min_value:
            return 1.0
        return (candidate.vector_score - min_value) / (max_value - min_value)

    if field_name == "bm25_score":
        if not candidate.bm25_hit or candidate.bm25_score is None:
            return 0.0
        if max_value == min_value:
            return 1.0
        return (candidate.bm25_score - min_value) / (max_value - min_value)

    raise ValueError(f"Unsupported normalization field: {field_name}")


def _apply_final_score(candidate: HybridCandidate) -> HybridCandidate:
    dual_hit_bonus = 1.0 if candidate.vector_hit and candidate.bm25_hit else 0.0
    final_score = (
        0.50 * (candidate.normalized_rrf_score or 0.0)
        + 0.20 * (candidate.normalized_vector_score or 0.0)
        + 0.20 * (candidate.normalized_bm25_score or 0.0)
        + 0.10 * dual_hit_bonus
    )
    return HybridCandidate(
        chunk_id=candidate.chunk_id,
        projection=candidate.projection,
        vector_hit=candidate.vector_hit,
        bm25_hit=candidate.bm25_hit,
        vector_score=candidate.vector_score,
        bm25_score=candidate.bm25_score,
        rank_vector=candidate.rank_vector,
        rank_bm25=candidate.rank_bm25,
        match_sources=candidate.match_sources,
        rrf_score=candidate.rrf_score,
        normalized_rrf_score=candidate.normalized_rrf_score,
        normalized_vector_score=candidate.normalized_vector_score,
        normalized_bm25_score=candidate.normalized_bm25_score,
        dual_hit_bonus=dual_hit_bonus,
        final_score=final_score,
    )


def _merge_match_sources(
    left: tuple[str, ...],
    right: tuple[str, ...],
) -> tuple[str, ...]:
    merged: list[str] = []
    for value in (*left, *right):
        if value not in merged:
            merged.append(value)
    return tuple(merged)
