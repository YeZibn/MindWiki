"""PostgreSQL-backed helpers for vector indexing state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from mindwiki.infrastructure.database import get_database_url


@dataclass(frozen=True, slots=True)
class ChunkEmbeddingSource:
    """Chunk projection needed for embedding generation and vector writes."""

    chunk_id: UUID
    document_id: UUID
    section_id: UUID | None
    document_title: str
    section_title: str | None
    chunk_text: str
    source_type: str
    document_type: str
    document_tags: tuple[str, ...]
    imported_at: datetime | None


@dataclass(frozen=True, slots=True)
class ChunkEmbeddingMetadataUpdate:
    """Chunk embedding metadata written back to PostgreSQL."""

    chunk_id: UUID
    embedding_ref: str
    embedding_provider: str
    embedding_model: str
    embedding_version: str
    embedding_dim: int


class VectorIndexRepository(Protocol):
    """Repository contract for vector indexing workflows."""

    def list_document_chunks_for_embedding(self, document_id: UUID) -> tuple[ChunkEmbeddingSource, ...]: ...

    def update_chunk_embedding_metadata(
        self,
        updates: tuple[ChunkEmbeddingMetadataUpdate, ...],
    ) -> None: ...


class PostgresVectorIndexRepository:
    """Load chunk embedding sources and persist embedding metadata."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def list_document_chunks_for_embedding(self, document_id: UUID) -> tuple[ChunkEmbeddingSource, ...]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        c.id AS chunk_id,
                        d.id AS document_id,
                        c.section_id,
                        d.title AS document_title,
                        s.title AS section_title,
                        c.content_text AS chunk_text,
                        src.source_type,
                        d.document_type,
                        d.imported_at,
                        COALESCE(
                            ARRAY_AGG(DISTINCT t.tag_name) FILTER (WHERE t.tag_name IS NOT NULL),
                            '{}'
                        ) AS document_tags
                    FROM chunks c
                    JOIN documents d ON d.id = c.document_id
                    JOIN sources src ON src.id = d.source_id
                    LEFT JOIN sections s ON s.id = c.section_id
                    LEFT JOIN document_tags dt ON dt.document_id = d.id
                    LEFT JOIN tags t ON t.id = dt.tag_id
                    WHERE c.document_id = %s
                      AND d.deleted_at IS NULL
                      AND c.deleted_at IS NULL
                      AND d.status = 'active'
                    GROUP BY
                        c.id,
                        d.id,
                        s.id,
                        src.id
                    ORDER BY c.chunk_index ASC
                    """,
                    (document_id,),
                )
                rows = cursor.fetchall()

        return tuple(
            ChunkEmbeddingSource(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                section_id=row["section_id"],
                document_title=str(row["document_title"] or ""),
                section_title=row["section_title"],
                chunk_text=str(row["chunk_text"] or ""),
                source_type=str(row["source_type"] or ""),
                document_type=str(row["document_type"] or ""),
                document_tags=tuple(row["document_tags"] or ()),
                imported_at=row["imported_at"],
            )
            for row in rows
        )

    def update_chunk_embedding_metadata(
        self,
        updates: tuple[ChunkEmbeddingMetadataUpdate, ...],
    ) -> None:
        if not updates:
            return

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                for update in updates:
                    cursor.execute(
                        """
                        UPDATE chunks
                        SET
                            embedding_ref = %s,
                            embedding_provider = %s,
                            embedding_model = %s,
                            embedding_version = %s,
                            embedding_dim = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (
                            update.embedding_ref,
                            update.embedding_provider,
                            update.embedding_model,
                            update.embedding_version,
                            update.embedding_dim,
                            update.chunk_id,
                        ),
                    )
            connection.commit()


def build_vector_index_repository() -> VectorIndexRepository | None:
    """Create the default PostgreSQL-backed vector index repository."""

    database_url = get_database_url()
    if not database_url:
        return None
    return PostgresVectorIndexRepository(database_url)
