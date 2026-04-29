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
