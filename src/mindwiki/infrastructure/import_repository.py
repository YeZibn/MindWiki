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

from mindwiki.application.import_models import ImportDirectoryRequest, ImportFileRequest
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
    def create_directory_import_jobs(
        self,
        request: ImportDirectoryRequest,
        supported_files: tuple[Path, ...],
        unsupported_files: tuple[Path, ...],
        empty_files: tuple[Path, ...],
    ) -> tuple[UUID, tuple[UUID, ...]]: ...

    def create_import_job(
        self,
        request: ImportFileRequest,
        detected_file_type: str | None,
    ) -> UUID: ...

    def update_import_job_status(
        self,
        import_job_id: UUID,
        status: str,
        *,
        error_message: str | None = None,
    ) -> None: ...

    def persist_markdown_import(
        self,
        import_job_id: UUID,
        request: ImportFileRequest,
        parsed: ParsedMarkdownDocument,
    ) -> PersistedImportResult: ...


class PostgresImportRepository:
    """Persist import artifacts into the local PostgreSQL schema."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def persist_markdown_import(
        self,
        import_job_id: UUID,
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

    def create_directory_import_jobs(
        self,
        request: ImportDirectoryRequest,
        supported_files: tuple[Path, ...],
        unsupported_files: tuple[Path, ...],
        empty_files: tuple[Path, ...],
    ) -> tuple[UUID, tuple[UUID, ...]]:
        path = request.path.expanduser().resolve()
        now = datetime.now()
        parent_payload = json.dumps(
            {
                "path": str(path),
                "import_type": "dir",
                "recursive": request.recursive,
                "tags": list(request.tags),
                "source_note": request.source_note,
                "supported_file_count": len(supported_files),
                "unsupported_file_count": len(unsupported_files),
                "empty_file_count": len(empty_files),
            },
            ensure_ascii=True,
        )
        child_job_ids: list[UUID] = []

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                parent_job_id = self._insert_import_job(
                    cursor,
                    path=path,
                    input_payload=parent_payload,
                    status="success",
                    now=now,
                    job_type="dir",
                    parent_job_id=None,
                )

                for file_path in supported_files:
                    child_payload = json.dumps(
                        {
                            "path": str(file_path),
                            "import_type": "file",
                            "recursive": request.recursive,
                            "tags": list(request.tags),
                            "source_note": request.source_note,
                            "detected_file_type": file_path.suffix.lower() or None,
                            "parent_job_id": str(parent_job_id),
                        },
                        ensure_ascii=True,
                    )
                    child_job_id = self._insert_import_job(
                        cursor,
                        path=file_path,
                        input_payload=child_payload,
                        status="pending",
                        now=None,
                        job_type="file",
                        parent_job_id=parent_job_id,
                    )
                    child_job_ids.append(child_job_id)

                for file_path in unsupported_files:
                    child_payload = json.dumps(
                        {
                            "path": str(file_path),
                            "import_type": "file",
                            "recursive": request.recursive,
                            "tags": list(request.tags),
                            "source_note": request.source_note,
                            "detected_file_type": file_path.suffix.lower() or None,
                            "parent_job_id": str(parent_job_id),
                            "skip_reason": "unsupported_file_type",
                        },
                        ensure_ascii=True,
                    )
                    child_job_id = self._insert_import_job(
                        cursor,
                        path=file_path,
                        input_payload=child_payload,
                        status="skipped",
                        now=now,
                        job_type="file",
                        parent_job_id=parent_job_id,
                        error_message="unsupported_file_type",
                    )
                    child_job_ids.append(child_job_id)

                for file_path in empty_files:
                    child_payload = json.dumps(
                        {
                            "path": str(file_path),
                            "import_type": "file",
                            "recursive": request.recursive,
                            "tags": list(request.tags),
                            "source_note": request.source_note,
                            "detected_file_type": file_path.suffix.lower() or None,
                            "parent_job_id": str(parent_job_id),
                            "skip_reason": "empty_file",
                        },
                        ensure_ascii=True,
                    )
                    child_job_id = self._insert_import_job(
                        cursor,
                        path=file_path,
                        input_payload=child_payload,
                        status="skipped",
                        now=now,
                        job_type="file",
                        parent_job_id=parent_job_id,
                        error_message="empty_file",
                    )
                    child_job_ids.append(child_job_id)
            connection.commit()

        return parent_job_id, tuple(child_job_ids)

    def create_import_job(
        self,
        request: ImportFileRequest,
        detected_file_type: str | None,
    ) -> UUID:
        path = request.path.expanduser().resolve()
        input_payload = json.dumps(
            {
                "path": str(path),
                "import_type": "file",
                "tags": list(request.tags),
                "source_note": request.source_note,
                "detected_file_type": detected_file_type,
            },
            ensure_ascii=True,
        )

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                import_job_id = self._insert_import_job(
                    cursor,
                    path=path,
                    input_payload=input_payload,
                    status="pending",
                    now=None,
                    job_type="file",
                    parent_job_id=None,
                )
            connection.commit()

        return import_job_id

    def update_import_job_status(
        self,
        import_job_id: UUID,
        status: str,
        *,
        error_message: str | None = None,
    ) -> None:
        finished_at = datetime.now() if status in {"success", "failed", "skipped", "cancelled"} else None
        started_at = datetime.now() if status == "running" else None

        with psycopg.connect(self._database_url, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE import_jobs
                    SET
                        status = %s,
                        error_message = %s,
                        started_at = COALESCE(started_at, %s),
                        finished_at = COALESCE(%s, finished_at),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        status,
                        error_message,
                        started_at,
                        finished_at,
                        import_job_id,
                    ),
                )
            connection.commit()

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
        status: str,
        now: datetime | None,
        job_type: str,
        parent_job_id: UUID | None,
        error_message: str | None = None,
    ) -> UUID:
        cursor.execute(
            """
            INSERT INTO import_jobs (
                parent_job_id,
                job_type,
                status,
                input_path,
                input_payload,
                error_message,
                retry_count,
                started_at,
                finished_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                parent_job_id,
                job_type,
                status,
                str(path),
                input_payload,
                error_message,
                0,
                now,
                now if status in {"success", "skipped"} else None,
            ),
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
