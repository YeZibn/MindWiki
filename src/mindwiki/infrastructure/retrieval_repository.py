"""PostgreSQL-backed retrieval projection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import psycopg
from psycopg.rows import dict_row

from mindwiki.application.retrieval_models import ChunkLocation, ChunkProjection, RetrievalFilters
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


def build_projection_query(filters: RetrievalFilters, *, limit: int) -> ProjectionQuery:
    """Build the first-stage projection query and strong filters."""

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
