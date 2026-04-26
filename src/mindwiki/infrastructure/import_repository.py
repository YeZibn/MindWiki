"""PostgreSQL-backed import persistence helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Protocol
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from mindwiki.application.import_models import ImportFileRequest
from mindwiki.ingestion.markdown import ParsedMarkdownDocument
from mindwiki.infrastructure.database import get_database_url


@dataclass(slots=True)
class PersistedImportResult:
    import_job_id: UUID
    source_id: UUID
    document_id: UUID
    section_count: int
    chunk_count: int


class ImportRepository(Protocol):
    def persist_markdown_import(
        self,
        request: ImportFileRequest,
        parsed: ParsedMarkdownDocument,
    ) -> PersistedImportResult: ...


class PostgresImportRepository:
    """Persist import artifacts into the local PostgreSQL schema."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def persist_markdown_import(
        self,
        request: ImportFileRequest,
        parsed: ParsedMarkdownDocument,
    ) -> PersistedImportResult:
        path = request.path.expanduser().resolve()
        content_hash = hashlib.sha256(parsed.raw_text.encode("utf-8")).hexdigest()
        title = parsed.title_candidates[0].value if parsed.title_candidates else path.stem
        now = datetime.now()
        input_payload = json.dumps(
            {
                "path": str(path),
                "tags": list(request.tags),
                "source_note": request.source_note,
            },
            ensure_ascii=True,
        )

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                source_id = self._insert_source(cursor, path, request.source_note)
                import_job_id = self._insert_import_job(cursor, path, input_payload, now)
                document_id = self._insert_document(
                    cursor,
                    source_id=source_id,
                    import_job_id=import_job_id,
                    path=path,
                    title=title,
                    content_hash=content_hash,
                    imported_at=now,
                )
                section_count, chunk_count = self._insert_sections_and_chunks(
                    cursor,
                    document_id=document_id,
                    parsed=parsed,
                )
            connection.commit()

        return PersistedImportResult(
            import_job_id=import_job_id,
            source_id=source_id,
            document_id=document_id,
            section_count=section_count,
            chunk_count=chunk_count,
        )

    @staticmethod
    def _insert_source(cursor: psycopg.Cursor[dict], path: Path, source_note: str | None) -> UUID:
        cursor.execute(
            """
            INSERT INTO sources (
                source_type,
                source_uri,
                file_path,
                import_method,
                source_note,
                is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            ("markdown", path.as_uri(), str(path), "cli_file", source_note, True),
        )
        row = cursor.fetchone()
        return row["id"]

    @staticmethod
    def _insert_import_job(
        cursor: psycopg.Cursor[dict],
        path: Path,
        input_payload: str,
        now: datetime,
    ) -> UUID:
        cursor.execute(
            """
            INSERT INTO import_jobs (
                job_type,
                status,
                input_path,
                input_payload,
                retry_count,
                started_at,
                finished_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            ("file", "success", str(path), input_payload, 0, now, now),
        )
        row = cursor.fetchone()
        return row["id"]

    @staticmethod
    def _insert_document(
        cursor: psycopg.Cursor[dict],
        *,
        source_id: UUID,
        import_job_id: UUID,
        path: Path,
        title: str,
        content_hash: str,
        imported_at: datetime,
    ) -> UUID:
        cursor.execute(
            """
            INSERT INTO documents (
                source_id,
                import_job_id,
                title,
                document_type,
                content_hash,
                source_native_key,
                file_path,
                summary,
                status,
                imported_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                source_id,
                import_job_id,
                title,
                "markdown",
                content_hash,
                path.name,
                str(path),
                None,
                "active",
                imported_at,
            ),
        )
        row = cursor.fetchone()
        return row["id"]

    @staticmethod
    def _insert_sections_and_chunks(
        cursor: psycopg.Cursor[dict],
        *,
        document_id: UUID,
        parsed: ParsedMarkdownDocument,
    ) -> tuple[int, int]:
        section_id_stack: list[tuple[int, UUID]] = []
        section_count = 0
        chunk_count = 0

        for index, section in enumerate(parsed.sections):
            while section_id_stack and section.level != 0 and section_id_stack[-1][0] >= section.level:
                section_id_stack.pop()

            parent_section_id = section_id_stack[-1][1] if section.level != 0 and section_id_stack else None

            cursor.execute(
                """
                INSERT INTO sections (
                    document_id,
                    parent_section_id,
                    title,
                    level,
                    order_index,
                    start_offset,
                    end_offset
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    document_id,
                    parent_section_id,
                    section.title,
                    section.level,
                    index,
                    None,
                    None,
                ),
            )
            section_row = cursor.fetchone()
            section_id = section_row["id"]
            section_count += 1

            if section.level != 0:
                section_id_stack.append((section.level, section_id))

            if not section.content:
                continue

            cursor.execute(
                """
                INSERT INTO chunks (
                    document_id,
                    section_id,
                    chunk_index,
                    content_text,
                    token_count,
                    start_offset,
                    end_offset,
                    page_number,
                    embedding_ref
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    document_id,
                    section_id,
                    chunk_count,
                    section.content,
                    None,
                    None,
                    None,
                    None,
                    None,
                ),
            )
            cursor.fetchone()
            chunk_count += 1

        return section_count, chunk_count


def build_import_repository() -> ImportRepository | None:
    """Create a PostgreSQL-backed repository if the database URL is configured."""

    database_url = get_database_url()
    if not database_url:
        return None
    return PostgresImportRepository(database_url)
