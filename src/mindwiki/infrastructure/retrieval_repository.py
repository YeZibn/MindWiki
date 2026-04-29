"""PostgreSQL-backed retrieval projection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import psycopg
from psycopg.rows import dict_row

from mindwiki.application.retrieval_models import (
    BM25Candidate,
    ChunkLocation,
    ChunkProjection,
    RetrievalFilters,
)
from mindwiki.infrastructure.database import get_database_url


@dataclass(frozen=True, slots=True)
class ProjectionQuery:
    """SQL plus parameters for one projection query."""

    sql: str
    params: tuple[object, ...]


class RetrievalRepository(Protocol):
    """Repository contract for retrieval-stage chunk projection queries."""

    def list_chunk_projections(
        self,
        filters: RetrievalFilters,
        *,
        limit: int = 100,
    ) -> tuple[ChunkProjection, ...]: ...

    def search_bm25(
        self,
        query_text: str,
        filters: RetrievalFilters,
        *,
        limit: int = 10,
    ) -> tuple[BM25Candidate, ...]: ...


class PostgresRetrievalRepository:
    """Load retrieval-ready chunk projections from PostgreSQL."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def list_chunk_projections(
        self,
        filters: RetrievalFilters,
        *,
        limit: int = 100,
    ) -> tuple[ChunkProjection, ...]:
        query = build_projection_query(filters, limit=limit)

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query.sql, query.params)
                rows = cursor.fetchall()

        return tuple(_row_to_chunk_projection(row) for row in rows)

    def search_bm25(
        self,
        query_text: str,
        filters: RetrievalFilters,
        *,
        limit: int = 10,
    ) -> tuple[BM25Candidate, ...]:
        query = build_bm25_query(query_text, filters, limit=limit)

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query.sql, query.params)
                rows = cursor.fetchall()

        return tuple(_row_to_bm25_candidate(row) for row in rows)


def build_projection_query(filters: RetrievalFilters, *, limit: int) -> ProjectionQuery:
    """Build the first-stage projection query and strong filters."""

    where_clauses, params = _build_strong_filter_clauses(filters)

    params.append(limit)

    sql = f"""
        SELECT
            c.id AS chunk_id,
            d.id AS document_id,
            c.section_id,
            d.title AS document_title,
            s.title AS section_title,
            c.content_text AS chunk_text,
            src.source_type,
            d.document_type,
            c.chunk_index,
            c.page_number,
            d.imported_at,
            COALESCE(
                ARRAY_AGG(DISTINCT t.tag_name) FILTER (WHERE t.tag_name IS NOT NULL),
                '{{}}'
            ) AS document_tags
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        JOIN sources src ON src.id = d.source_id
        LEFT JOIN sections s ON s.id = c.section_id
        LEFT JOIN document_tags dt ON dt.document_id = d.id
        LEFT JOIN tags t ON t.id = dt.tag_id
        WHERE {" AND ".join(where_clauses)}
        GROUP BY
            c.id,
            d.id,
            s.id,
            src.id
        ORDER BY
            d.imported_at DESC NULLS LAST,
            c.chunk_index ASC
        LIMIT %s
    """.strip()
    return ProjectionQuery(sql=sql, params=tuple(params))


def build_bm25_query(query_text: str, filters: RetrievalFilters, *, limit: int) -> ProjectionQuery:
    """Build the first-stage BM25-style PostgreSQL full-text query."""

    where_clauses, params = _build_strong_filter_clauses(filters)
    params.append(query_text)
    params.append(query_text)
    params.append(query_text)
    params.append(query_text)
    params.append(query_text)
    params.append(limit)

    sql = f"""
        WITH chunk_projection AS (
            SELECT
                c.id AS chunk_id,
                d.id AS document_id,
                c.section_id,
                d.title AS document_title,
                s.title AS section_title,
                c.content_text AS chunk_text,
                src.source_type,
                d.document_type,
                c.chunk_index,
                c.page_number,
                d.imported_at,
                COALESCE(
                    ARRAY_AGG(DISTINCT t.tag_name) FILTER (WHERE t.tag_name IS NOT NULL),
                    '{{}}'
                ) AS document_tags,
                COALESCE(
                    STRING_AGG(DISTINCT t.tag_name, ' ') FILTER (WHERE t.tag_name IS NOT NULL),
                    ''
                ) AS document_tags_text
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            JOIN sources src ON src.id = d.source_id
            LEFT JOIN sections s ON s.id = c.section_id
            LEFT JOIN document_tags dt ON dt.document_id = d.id
            LEFT JOIN tags t ON t.id = dt.tag_id
            WHERE {" AND ".join(where_clauses)}
            GROUP BY
                c.id,
                d.id,
                s.id,
                src.id
        ),
        scored AS (
            SELECT
                chunk_id,
                document_id,
                section_id,
                document_title,
                section_title,
                chunk_text,
                source_type,
                document_type,
                chunk_index,
                page_number,
                imported_at,
                document_tags,
                ts_rank_cd(
                    setweight(to_tsvector('simple', COALESCE(document_title, '')), 'A') ||
                    setweight(to_tsvector('simple', COALESCE(section_title, '')), 'B') ||
                    setweight(to_tsvector('simple', COALESCE(document_tags_text, '')), 'C') ||
                    setweight(to_tsvector('simple', COALESCE(chunk_text, '')), 'D'),
                    websearch_to_tsquery('simple', %s)
                ) AS bm25_score,
                (to_tsvector('simple', COALESCE(document_title, '')) @@ websearch_to_tsquery('simple', %s)) AS match_document_title,
                (to_tsvector('simple', COALESCE(section_title, '')) @@ websearch_to_tsquery('simple', %s)) AS match_section_title,
                (to_tsvector('simple', COALESCE(document_tags_text, '')) @@ websearch_to_tsquery('simple', %s)) AS match_document_tags,
                (to_tsvector('simple', COALESCE(chunk_text, '')) @@ websearch_to_tsquery('simple', %s)) AS match_chunk_text
            FROM chunk_projection
        )
        SELECT
            chunk_id,
            document_id,
            section_id,
            document_title,
            section_title,
            chunk_text,
            source_type,
            document_type,
            chunk_index,
            page_number,
            imported_at,
            document_tags,
            bm25_score,
            match_document_title,
            match_section_title,
            match_document_tags,
            match_chunk_text
        FROM scored
        WHERE bm25_score > 0
        ORDER BY
            bm25_score DESC,
            imported_at DESC NULLS LAST,
            chunk_index ASC
        LIMIT %s
    """.strip()
    return ProjectionQuery(sql=sql, params=tuple(params))


def build_retrieval_repository() -> RetrievalRepository | None:
    """Create a PostgreSQL-backed retrieval repository if configured."""

    database_url = get_database_url()
    if not database_url:
        return None
    return PostgresRetrievalRepository(database_url)


def _row_to_chunk_projection(row: dict[str, object]) -> ChunkProjection:
    return ChunkProjection(
        chunk_id=row["chunk_id"],
        document_id=row["document_id"],
        section_id=row["section_id"],
        document_title=str(row["document_title"] or ""),
        section_title=row["section_title"],
        chunk_text=str(row["chunk_text"] or ""),
        source_type=str(row["source_type"] or ""),
        document_type=str(row["document_type"] or ""),
        document_tags=tuple(row["document_tags"] or ()),
        location=ChunkLocation(
            chunk_index=int(row["chunk_index"]),
            section_id=row["section_id"],
            page_number=row["page_number"],
            imported_at=row["imported_at"],
        ),
    )


def _row_to_bm25_candidate(row: dict[str, object]) -> BM25Candidate:
    match_sources: list[str] = []
    if row["match_document_title"]:
        match_sources.append("document_title")
    if row["match_section_title"]:
        match_sources.append("section_title")
    if row["match_document_tags"]:
        match_sources.append("document_tags")
    if row["match_chunk_text"]:
        match_sources.append("chunk_text")

    return BM25Candidate(
        projection=_row_to_chunk_projection(row),
        score=float(row["bm25_score"]),
        match_sources=tuple(match_sources),
    )


def _build_strong_filter_clauses(filters: RetrievalFilters) -> tuple[list[str], list[object]]:
    where_clauses = [
        "d.deleted_at IS NULL",
        "c.deleted_at IS NULL",
        "d.status = 'active'",
    ]
    params: list[object] = []

    if filters.source_types:
        where_clauses.append("src.source_type = ANY(%s)")
        params.append(list(filters.source_types))

    if filters.document_scope:
        where_clauses.append("d.id = ANY(%s)")
        params.append(list(filters.document_scope))

    if filters.tags:
        where_clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM document_tags dt_filter
                JOIN tags t_filter ON t_filter.id = dt_filter.tag_id
                WHERE dt_filter.document_id = d.id
                  AND t_filter.tag_name = ANY(%s)
            )
            """.strip()
        )
        params.append(list(filters.tags))

    if filters.time_range is not None and filters.time_range.start_time is not None:
        where_clauses.append("d.imported_at >= %s")
        params.append(filters.time_range.start_time)

    if filters.time_range is not None and filters.time_range.end_time is not None:
        where_clauses.append("d.imported_at <= %s")
        params.append(filters.time_range.end_time)

    return where_clauses, params
