"""Structured context builder for step 9.5."""

from __future__ import annotations

from mindwiki.application.retrieval_models import (
    ContextBuildResult,
    ContextEvidenceItem,
    ContextSubQuerySection,
    RerankedSubQueryCandidate,
    SubQueryRerankResult,
)


MAX_PRIMARY_EVIDENCE_PER_SUB_QUERY = 2


class ContextBuilderService:
    """Build structured context sections from reranked sub-query results."""

    def build_context(
        self,
        rerank_results: tuple[SubQueryRerankResult, ...],
    ) -> ContextBuildResult:
        sections = tuple(self._build_section(result) for result in rerank_results)
        return ContextBuildResult(sections=sections)

    def _build_section(self, result: SubQueryRerankResult) -> ContextSubQuerySection:
        selected_candidates = result.reranked_candidates[:MAX_PRIMARY_EVIDENCE_PER_SUB_QUERY]
        merged_candidates = _merge_adjacent_candidates(selected_candidates)
        evidence_items = tuple(
            ContextEvidenceItem(
                chunk_ids=item["chunk_ids"],
                document_id=item["document_id"],
                section_id=item["section_id"],
                document_title=item["document_title"],
                section_title=item["section_title"],
                source_type=item["source_type"],
                chunk_text=item["chunk_text"],
                location=item["location"],
                rerank_score=item["rerank_score"],
                evidence_role="primary" if index == 0 else "supporting",
            )
            for index, item in enumerate(merged_candidates)
        )
        return ContextSubQuerySection(
            sub_query_id=result.sub_query_id,
            sub_query_text=result.sub_query_text,
            evidence_items=evidence_items,
        )


def _merge_adjacent_candidates(
    candidates: tuple[RerankedSubQueryCandidate, ...],
) -> tuple[dict[str, object], ...]:
    if not candidates:
        return ()

    merged_items: list[dict[str, object]] = []
    current = _candidate_to_item(candidates[0])

    for candidate in candidates[1:]:
        if _can_merge(current, candidate):
            current = _merge_item_with_candidate(current, candidate)
            continue
        merged_items.append(current)
        current = _candidate_to_item(candidate)

    merged_items.append(current)
    return tuple(merged_items)


def _candidate_to_item(candidate: RerankedSubQueryCandidate) -> dict[str, object]:
    projection = candidate.projection
    return {
        "chunk_ids": (candidate.chunk_id,),
        "document_id": projection.document_id,
        "section_id": projection.section_id,
        "document_title": projection.document_title,
        "section_title": projection.section_title,
        "source_type": projection.source_type,
        "chunk_text": projection.chunk_text,
        "location": projection.location,
        "rerank_score": candidate.rerank_score,
        "chunk_index": projection.location.chunk_index,
    }


def _can_merge(current: dict[str, object], candidate: RerankedSubQueryCandidate) -> bool:
    projection = candidate.projection
    if current["document_id"] != projection.document_id:
        return False
    current_chunk_index = current["chunk_index"]
    if not isinstance(current_chunk_index, int):
        return False
    return projection.location.chunk_index == current_chunk_index + 1


def _merge_item_with_candidate(
    current: dict[str, object],
    candidate: RerankedSubQueryCandidate,
) -> dict[str, object]:
    projection = candidate.projection
    current_chunk_ids = current["chunk_ids"]
    assert isinstance(current_chunk_ids, tuple)
    current_chunk_text = current["chunk_text"]
    assert isinstance(current_chunk_text, str)
    current_rerank_score = current["rerank_score"]
    assert isinstance(current_rerank_score, float)

    return {
        "chunk_ids": (*current_chunk_ids, candidate.chunk_id),
        "document_id": current["document_id"],
        "section_id": current["section_id"],
        "document_title": current["document_title"],
        "section_title": current["section_title"],
        "source_type": current["source_type"],
        "chunk_text": f"{current_chunk_text}\n\n{projection.chunk_text}",
        "location": current["location"],
        "rerank_score": max(current_rerank_score, candidate.rerank_score),
        "chunk_index": projection.location.chunk_index,
    }
