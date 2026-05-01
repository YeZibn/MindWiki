"""Shared models for retrieval projections and filters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TimeRange:
    """First-stage retrieval time range, based on import timestamps."""

    start_time: datetime | None = None
    end_time: datetime | None = None


@dataclass(frozen=True, slots=True)
class RetrievalFilters:
    """Strong filters applied before retrieval execution."""

    tags: tuple[str, ...] = ()
    source_types: tuple[str, ...] = ()
    document_scope: tuple[UUID, ...] = ()
    time_range: TimeRange | None = None


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    """Unified retrieval query input for the first retrieval stage."""

    query: str
    filters: RetrievalFilters = field(default_factory=RetrievalFilters)
    top_k: int = 10
    retrieval_mode: str = "bm25_only"


@dataclass(frozen=True, slots=True)
class QueryDecomposition:
    """First-stage query decomposition result for retrieval orchestration."""

    query: str
    decomposition_mode: str = "none"
    sub_queries: tuple[str, ...] = ()
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class QueryExpansion:
    """First-stage fixed query expansion payload for one retrieval unit."""

    query: str
    base_query: str
    step_back_query: str
    hyde_query: str
    use_step_back: bool = True
    use_hyde: bool = True


@dataclass(frozen=True, slots=True)
class SubQueryCandidate:
    """Merged candidate inside one sub-query after 4-route retrieval."""

    chunk_id: UUID
    projection: ChunkProjection
    hit_sources: tuple[str, ...] = field(default_factory=tuple)
    rank_base_bm25: int | None = None
    rank_base_vector: int | None = None
    rank_step_back_vector: int | None = None
    rank_hyde_vector: int | None = None
    base_bm25_score: float | None = None
    base_vector_score: float | None = None
    step_back_vector_score: float | None = None
    hyde_vector_score: float | None = None
    fused_rrf_score: float | None = None


@dataclass(frozen=True, slots=True)
class SubQueryResult:
    """Independent candidate set for one sub-query in step 9.3."""

    sub_query_id: str
    sub_query_text: str
    base_query: str
    step_back_query: str
    hyde_query: str
    candidates: tuple[SubQueryCandidate, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RerankedSubQueryCandidate:
    """Reranked candidate inside one sub-query after step 9.4."""

    chunk_id: UUID
    projection: ChunkProjection
    hit_sources: tuple[str, ...] = field(default_factory=tuple)
    fused_rrf_score: float | None = None
    rerank_score: float = 0.0
    rerank_reason: str = ""


@dataclass(frozen=True, slots=True)
class SubQueryRerankResult:
    """Reranked candidate set for one sub-query in step 9.4."""

    sub_query_id: str
    sub_query_text: str
    reranked_candidates: tuple[RerankedSubQueryCandidate, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ContextEvidenceItem:
    """One structured evidence item prepared for context assembly."""

    chunk_ids: tuple[UUID, ...]
    document_id: UUID
    section_id: UUID | None
    document_title: str
    section_title: str | None
    source_type: str
    chunk_text: str
    location: ChunkLocation
    rerank_score: float
    evidence_role: str = "supporting"


@dataclass(frozen=True, slots=True)
class ContextSubQuerySection:
    """Structured context section for one sub-query."""

    sub_query_id: str
    sub_query_text: str
    evidence_items: tuple[ContextEvidenceItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ContextBuildResult:
    """Structured context package built from reranked sub-query results."""

    sections: tuple[ContextSubQuerySection, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class CitationPayload:
    """Unified citation payload for one evidence item."""

    citation_id: str
    sub_query_id: str
    chunk_id: UUID
    document_id: UUID
    section_id: UUID | None
    document_title: str
    section_title: str | None
    source_type: str
    snippet: str
    match_sources: tuple[str, ...] = field(default_factory=tuple)
    evidence_role: str = "supporting"
    location: ChunkLocation = field(default_factory=lambda: ChunkLocation(chunk_index=0))


@dataclass(frozen=True, slots=True)
class CitationBuildResult:
    """Structured citation package derived from built context."""

    citations: tuple[CitationPayload, ...] = field(default_factory=tuple)


ANSWER_CONFIDENCE_VALUES: tuple[str, ...] = ("high", "medium", "low")


@dataclass(frozen=True, slots=True)
class AnswerGenerationResult:
    """Structured first-stage answer generation result for QA only."""

    question: str
    answer: str
    sources: tuple[CitationPayload, ...] = field(default_factory=tuple)
    confidence: str = "low"


@dataclass(frozen=True, slots=True)
class QARequest:
    """Unified first-stage QA request for the main orchestration entrypoint."""

    question: str
    filters: RetrievalFilters = field(default_factory=RetrievalFilters)
    top_k: int = 5


@dataclass(frozen=True, slots=True)
class QAOrchestrationResult:
    """Unified first-stage QA orchestration result."""

    question: str
    decomposition: QueryDecomposition
    rerank_results: tuple[SubQueryRerankResult, ...] = field(default_factory=tuple)
    context_result: ContextBuildResult = field(default_factory=ContextBuildResult)
    citation_result: CitationBuildResult = field(default_factory=CitationBuildResult)
    answer_result: AnswerGenerationResult = field(
        default_factory=lambda: AnswerGenerationResult(question="", answer="")
    )


@dataclass(frozen=True, slots=True)
class ChunkLocation:
    """Minimal location payload for first-stage chunk retrieval."""

    chunk_index: int
    section_id: UUID | None = None
    page_number: int | None = None
    imported_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ChunkProjection:
    """Projected chunk fields required by the first retrieval stage."""

    chunk_id: UUID
    document_id: UUID
    section_id: UUID | None
    document_title: str
    section_title: str | None
    chunk_text: str
    source_type: str
    document_type: str
    document_tags: tuple[str, ...] = field(default_factory=tuple)
    location: ChunkLocation = field(default_factory=lambda: ChunkLocation(chunk_index=0))


@dataclass(frozen=True, slots=True)
class BM25Candidate:
    """Minimal scored retrieval candidate for the BM25 stage."""

    projection: ChunkProjection
    score: float
    match_sources: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class VectorCandidate:
    """Minimal scored retrieval candidate for the vector stage."""

    projection: ChunkProjection
    score: float
    match_sources: tuple[str, ...] = ("vector",)


@dataclass(frozen=True, slots=True)
class HybridCandidate:
    """Merged hybrid candidate before fusion scoring is applied."""

    chunk_id: UUID
    projection: ChunkProjection
    vector_hit: bool = False
    bm25_hit: bool = False
    vector_score: float | None = None
    bm25_score: float | None = None
    rank_vector: int | None = None
    rank_bm25: int | None = None
    match_sources: tuple[str, ...] = field(default_factory=tuple)
    rrf_score: float | None = None
    normalized_rrf_score: float | None = None
    normalized_vector_score: float | None = None
    normalized_bm25_score: float | None = None
    dual_hit_bonus: float | None = None
    final_score: float | None = None


@dataclass(frozen=True, slots=True)
class ChunkHit:
    """Unified retrieval hit returned to upper layers."""

    chunk_id: UUID
    document_id: UUID
    section_id: UUID | None
    document_title: str
    section_title: str | None
    chunk_text: str
    source_type: str
    location: ChunkLocation
    score: float
    match_sources: tuple[str, ...] = field(default_factory=tuple)
    score_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Unified retrieval result payload for one retrieval query."""

    query: str
    retrieval_mode: str
    hits: tuple[ChunkHit, ...] = field(default_factory=tuple)
