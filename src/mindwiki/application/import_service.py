"""Application service for import workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import psycopg

from mindwiki.ingestion.markdown import parse_markdown
from mindwiki.ingestion.pdf import PdfReadError, PdfTextExtractionError, parse_pdf
from mindwiki.application.import_models import ImportDirectoryRequest, ImportFileRequest
from mindwiki.infrastructure.import_repository import (
    DirectoryChildJob,
    DirectoryImportJobSummary,
    ImportRepository,
    build_import_repository,
)
from mindwiki.application.vector_index_service import VectorIndexService, build_vector_index_service
from mindwiki.observability.logger import LogEvent, LogTimer, ensure_request_id, get_logger


SUPPORTED_FILE_TYPES = {".md", ".pdf"}
_LOGGER = get_logger("mindwiki.import")


@dataclass(slots=True)
class CommandResult:
    exit_code: int
    message: str


@dataclass(slots=True)
class DirectoryScanResult:
    scanned_files: tuple[Path, ...]
    supported_files: tuple[Path, ...]
    unsupported_files: tuple[Path, ...]
    empty_files: tuple[Path, ...]


@dataclass(slots=True)
class DirectoryExecutionSummary:
    success_jobs: int = 0
    failed_jobs: int = 0
    skipped_jobs: int = 0

    def as_payload(self) -> dict[str, int]:
        return {
            "success_jobs": self.success_jobs,
            "failed_jobs": self.failed_jobs,
            "executed_skipped_jobs": self.skipped_jobs,
        }


class ImportService:
    """Coordinates CLI-facing import requests."""

    def __init__(
        self,
        repository: ImportRepository | None = None,
        vector_index_service: VectorIndexService | None = None,
    ) -> None:
        self._repository = repository if repository is not None else build_import_repository()
        self._vector_index_service = (
            vector_index_service if vector_index_service is not None else build_vector_index_service()
        )

    def import_file(self, request: ImportFileRequest) -> CommandResult:
        path = request.path.expanduser().resolve()
        request_id = ensure_request_id(
            {
                "request_id": f"import-file:{path}",
            }
        )
        timer = LogTimer()
        _LOGGER.emit(
            LogEvent(
                event="import_file_started",
                request_id=request_id,
                interface_name="import_file",
                stage="import_file",
                status="started",
                metadata={
                    "path": str(path),
                    "tag_count": len(request.tags),
                    "has_source_note": bool(request.source_note),
                },
            )
        )

        if not path.exists():
            _LOGGER.emit(
                LogEvent(
                    event="import_file_completed",
                    request_id=request_id,
                    interface_name="import_file",
                    stage="import_file",
                    status="failed",
                    duration_ms=timer.elapsed_ms(),
                    metadata={"path": str(path), "reason": "file_not_found"},
                )
            )
            return CommandResult(exit_code=1, message=f"File not found: {path}")

        if not path.is_file():
            _LOGGER.emit(
                LogEvent(
                    event="import_file_completed",
                    request_id=request_id,
                    interface_name="import_file",
                    stage="import_file",
                    status="failed",
                    duration_ms=timer.elapsed_ms(),
                    metadata={"path": str(path), "reason": "path_not_file"},
                )
            )
            return CommandResult(exit_code=1, message=f"Path is not a file: {path}")

        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_FILE_TYPES:
            supported_types = ", ".join(sorted(SUPPORTED_FILE_TYPES))
            _LOGGER.emit(
                LogEvent(
                    event="import_file_completed",
                    request_id=request_id,
                    interface_name="import_file",
                    stage="import_file",
                    status="failed",
                    duration_ms=timer.elapsed_ms(),
                    metadata={"path": str(path), "reason": "unsupported_file_type", "type": suffix},
                )
            )
            return CommandResult(
                exit_code=1,
                message=(
                    f"Unsupported file type: {suffix or '<none>'}. "
                    f"Supported types: {supported_types}"
                ),
            )

        if suffix == ".md":
            result = self._import_markdown_file(request, request_id=request_id)
        elif suffix == ".pdf":
            result = self._import_pdf_file(request, request_id=request_id)
        else:
            details = [
                "Single-file import request accepted.",
                f"path={path}",
                f"type={suffix}",
                "parsing=pending",
                "persistence=skipped",
            ]

            if request.tags:
                details.append(f"tags={','.join(request.tags)}")

            if request.source_note:
                details.append(f"source_note={request.source_note}")

            result = CommandResult(
                exit_code=0,
                message=" ".join(details),
            )
        _LOGGER.emit(
            LogEvent(
                event="import_file_completed",
                request_id=request_id,
                interface_name="import_file",
                stage="import_file",
                status="success" if result.exit_code == 0 else "failed",
                duration_ms=timer.elapsed_ms(),
                metadata={
                    "path": str(path),
                    "type": suffix,
                    "exit_code": result.exit_code,
                },
            )
        )
        return result

    def _safe_mark_failed(self, import_job_id: object, exc: Exception) -> None:
        if self._repository is None:
            return
        try:
            self._repository.update_import_job_status(
                import_job_id,
                "failed",
                error_message=f"{exc.__class__.__name__}: {exc}",
            )
        except psycopg.Error:
            pass

    def _import_markdown_file(
        self,
        request: ImportFileRequest,
        *,
        import_job_id: object | None = None,
        request_id: str | None = None,
    ) -> CommandResult:
        path = request.path.expanduser().resolve()
        suffix = path.suffix.lower()
        active_import_job_id = import_job_id

        if self._repository is not None:
            try:
                if active_import_job_id is None:
                    active_import_job_id = self._repository.create_import_job(request, suffix)
                self._repository.update_import_job_status(active_import_job_id, "running")
            except psycopg.Error as exc:
                return CommandResult(
                    exit_code=1,
                    message=(
                        "Single-file import failed. "
                        f"path={path} type={suffix} "
                        f"reason=database_error:{exc.__class__.__name__}"
                    ),
                )

        try:
            parsed = parse_markdown(path)
        except Exception as exc:
            if self._repository is not None and active_import_job_id is not None:
                self._safe_mark_failed(active_import_job_id, exc)
            return CommandResult(
                exit_code=1,
                message=(
                    "Single-file import failed. "
                    f"path={path} type={suffix} "
                    f"reason=parse_error:{exc.__class__.__name__}"
                ),
            )

        title = parsed.title_candidates[0].value if parsed.title_candidates else path.stem
        details = [
            "Single-file import request accepted.",
            f"path={path}",
            f"type={suffix}",
            f"title={title}",
            f"sections={len(parsed.sections)}",
        ]

        if self._repository is not None:
            try:
                persisted = self._repository.persist_markdown_import(active_import_job_id, request, parsed)
                self._repository.update_import_job_status(active_import_job_id, "success")
            except psycopg.Error as exc:
                if active_import_job_id is not None:
                    self._safe_mark_failed(active_import_job_id, exc)
                return CommandResult(
                    exit_code=1,
                    message=(
                        "Single-file import failed. "
                        f"path={path} type={suffix} "
                        f"reason=database_error:{exc.__class__.__name__} "
                        f"import_job_id={active_import_job_id}"
                    ),
                )
            else:
                vector_sync_details: list[str] = []
                if self._vector_index_service is not None:
                    try:
                        vector_result = self._vector_index_service.index_document(
                            persisted.document_id,
                            request_id=request_id,
                        )
                    except Exception as exc:
                        if active_import_job_id is not None:
                            self._safe_mark_failed(active_import_job_id, exc)
                        return CommandResult(
                            exit_code=1,
                            message=(
                                "Single-file import failed. "
                                f"path={path} type={suffix} "
                                f"reason=vector_index_error:{exc.__class__.__name__} "
                                f"import_job_id={active_import_job_id}"
                            ),
                        )
                    else:
                        vector_sync_details.extend(
                            [
                                "vector_sync=stored",
                                f"embedding_model={vector_result.embedding_model}",
                                f"embedding_dim={vector_result.embedding_dim}",
                                f"vector_collection={vector_result.collection_name}",
                            ]
                        )
                else:
                    vector_sync_details.extend(
                        [
                            "vector_sync=skipped",
                            "vector_reason=embedding_or_milvus_not_configured",
                        ]
                    )
                details.extend(
                    [
                        "persistence=stored",
                        f"import_job_id={persisted.import_job_id}",
                        f"source_id={persisted.source_id}",
                        f"document_id={persisted.document_id}",
                        f"chunks={persisted.chunk_count}",
                    ]
                )
                details.extend(vector_sync_details)
        else:
            details.append("persistence=skipped")
            details.append("reason=database_url_missing")

        if request.tags:
            details.append(f"tags={','.join(request.tags)}")

        if request.source_note:
            details.append(f"source_note={request.source_note}")

        return CommandResult(exit_code=0, message=" ".join(details))

    def _import_pdf_file(
        self,
        request: ImportFileRequest,
        *,
        import_job_id: object | None = None,
        request_id: str | None = None,
    ) -> CommandResult:
        path = request.path.expanduser().resolve()
        suffix = path.suffix.lower()
        active_import_job_id = import_job_id

        if self._repository is not None:
            try:
                if active_import_job_id is None:
                    active_import_job_id = self._repository.create_import_job(request, suffix)
                self._repository.update_import_job_status(active_import_job_id, "running")
            except psycopg.Error as exc:
                return CommandResult(
                    exit_code=1,
                    message=(
                        "Single-file import failed. "
                        f"path={path} type={suffix} "
                        f"reason=database_error:{exc.__class__.__name__}"
                    ),
                )

        try:
            parsed = parse_pdf(path)
        except PdfReadError:
            if self._repository is not None and active_import_job_id is not None:
                self._safe_mark_failed(active_import_job_id, PdfReadError("pdf_read_failed"))
            return CommandResult(
                exit_code=1,
                message=(
                    "Single-file import failed. "
                    f"path={path} type={suffix} "
                    "reason=pdf_read_failed"
                ),
            )
        except PdfTextExtractionError:
            if self._repository is not None and active_import_job_id is not None:
                self._safe_mark_failed(
                    active_import_job_id,
                    PdfTextExtractionError("pdf_text_extraction_failed"),
                )
            return CommandResult(
                exit_code=1,
                message=(
                    "Single-file import failed. "
                    f"path={path} type={suffix} "
                    "reason=pdf_text_extraction_failed"
                ),
            )

        title = parsed.title_candidates[0].value if parsed.title_candidates else path.stem
        details = [
            "Single-file import request accepted.",
            f"path={path}",
            f"type={suffix}",
            f"title={title}",
            f"pages={parsed.page_count}",
            f"sections={len(parsed.sections)}",
        ]

        if self._repository is not None:
            try:
                persisted = self._repository.persist_pdf_import(active_import_job_id, request, parsed)
                self._repository.update_import_job_status(active_import_job_id, "success")
            except psycopg.Error as exc:
                if active_import_job_id is not None:
                    self._safe_mark_failed(active_import_job_id, exc)
                return CommandResult(
                    exit_code=1,
                    message=(
                        "Single-file import failed. "
                        f"path={path} type={suffix} "
                        f"reason=database_error:{exc.__class__.__name__} "
                        f"import_job_id={active_import_job_id}"
                    ),
                )
            else:
                vector_sync_details: list[str] = []
                if self._vector_index_service is not None:
                    try:
                        vector_result = self._vector_index_service.index_document(
                            persisted.document_id,
                            request_id=request_id,
                        )
                    except Exception as exc:
                        if active_import_job_id is not None:
                            self._safe_mark_failed(active_import_job_id, exc)
                        return CommandResult(
                            exit_code=1,
                            message=(
                                "Single-file import failed. "
                                f"path={path} type={suffix} "
                                f"reason=vector_index_error:{exc.__class__.__name__} "
                                f"import_job_id={active_import_job_id}"
                            ),
                        )
                    else:
                        vector_sync_details.extend(
                            [
                                "vector_sync=stored",
                                f"embedding_model={vector_result.embedding_model}",
                                f"embedding_dim={vector_result.embedding_dim}",
                                f"vector_collection={vector_result.collection_name}",
                            ]
                        )
                else:
                    vector_sync_details.extend(
                        [
                            "vector_sync=skipped",
                            "vector_reason=embedding_or_milvus_not_configured",
                        ]
                    )
                details.extend(
                    [
                        "persistence=stored",
                        f"import_job_id={persisted.import_job_id}",
                        f"source_id={persisted.source_id}",
                        f"document_id={persisted.document_id}",
                        f"chunks={persisted.chunk_count}",
                    ]
                )
                details.extend(vector_sync_details)
        else:
            details.append("parsing=completed")
            details.append("persistence=skipped")
            details.append("reason=database_url_missing")

        if request.tags:
            details.append(f"tags={','.join(request.tags)}")

        if request.source_note:
            details.append(f"source_note={request.source_note}")

        return CommandResult(exit_code=0, message=" ".join(details))

    def _execute_directory_child_jobs(
        self,
        request: ImportDirectoryRequest,
        child_jobs: tuple[DirectoryChildJob, ...],
    ) -> DirectoryExecutionSummary:
        summary = DirectoryExecutionSummary()

        if self._repository is None:
            return summary

        for child_job in child_jobs:
            if child_job.status != "pending":
                continue

            child_request = ImportFileRequest(
                path=child_job.path,
                tags=request.tags,
                source_note=request.source_note,
            )

            if child_job.detected_file_type == ".md":
                result = self._import_markdown_file(
                    child_request,
                    import_job_id=child_job.import_job_id,
                )
                if result.exit_code == 0:
                    summary.success_jobs += 1
                else:
                    summary.failed_jobs += 1
                continue

            if child_job.detected_file_type == ".pdf":
                result = self._import_pdf_file(
                    child_request,
                    import_job_id=child_job.import_job_id,
                )
                if result.exit_code == 0:
                    summary.success_jobs += 1
                else:
                    summary.failed_jobs += 1

        return summary

    def import_directory(self, request: ImportDirectoryRequest) -> CommandResult:
        path = request.path.expanduser().resolve()
        request_id = ensure_request_id(
            {
                "request_id": f"import-dir:{path}",
            }
        )
        timer = LogTimer()
        _LOGGER.emit(
            LogEvent(
                event="import_directory_started",
                request_id=request_id,
                interface_name="import_directory",
                stage="import_directory",
                status="started",
                metadata={
                    "path": str(path),
                    "recursive": request.recursive,
                    "tag_count": len(request.tags),
                },
            )
        )

        if not path.exists():
            _LOGGER.emit(
                LogEvent(
                    event="import_directory_completed",
                    request_id=request_id,
                    interface_name="import_directory",
                    stage="import_directory",
                    status="failed",
                    duration_ms=timer.elapsed_ms(),
                    metadata={"path": str(path), "reason": "directory_not_found"},
                )
            )
            return CommandResult(exit_code=1, message=f"Directory not found: {path}")

        if not path.is_dir():
            _LOGGER.emit(
                LogEvent(
                    event="import_directory_completed",
                    request_id=request_id,
                    interface_name="import_directory",
                    stage="import_directory",
                    status="failed",
                    duration_ms=timer.elapsed_ms(),
                    metadata={"path": str(path), "reason": "path_not_directory"},
                )
            )
            return CommandResult(
                exit_code=1,
                message=f"Path is not a directory: {path}",
            )

        scan_result = scan_directory_files(path, recursive=request.recursive)
        details = [
            "Directory import request accepted.",
            f"path={path}",
            f"recursive={'true' if request.recursive else 'false'}",
            f"scanned_files={len(scan_result.scanned_files)}",
        ]

        if self._repository is not None:
            try:
                parent_job_id, child_jobs, job_summary = self._repository.create_directory_import_jobs(
                    request,
                    scan_result.supported_files,
                    scan_result.unsupported_files,
                    scan_result.empty_files,
                )
                execution_summary = self._execute_directory_child_jobs(request, child_jobs)
                self._repository.update_directory_import_summary(
                    parent_job_id,
                    execution_summary.as_payload(),
                )
            except psycopg.Error as exc:
                return CommandResult(
                    exit_code=1,
                    message=(
                        "Directory import failed. "
                        f"path={path} "
                        f"reason=database_error:{exc.__class__.__name__}"
                    ),
                )
            details.extend(
                [
                    f"supported_files={len(scan_result.supported_files)}",
                    f"unsupported_files={len(scan_result.unsupported_files)}",
                    f"empty_files={len(scan_result.empty_files)}",
                    "job_persistence=stored",
                    f"batch_job_id={parent_job_id}",
                    f"child_jobs={len(child_jobs)}",
                    f"success_jobs={execution_summary.success_jobs}",
                    f"failed_jobs={execution_summary.failed_jobs}",
                    f"executed_skipped_jobs={execution_summary.skipped_jobs}",
                ]
            )
        else:
            job_summary = DirectoryImportJobSummary(
                pending_jobs=len(scan_result.supported_files),
                skipped_jobs=len(scan_result.unsupported_files) + len(scan_result.empty_files),
                skipped_unsupported=len(scan_result.unsupported_files),
                skipped_empty=len(scan_result.empty_files),
                skipped_unchanged=0,
            )
            execution_summary = DirectoryExecutionSummary()
            details.extend(
                [
                    f"supported_files={len(scan_result.supported_files)}",
                    f"unsupported_files={len(scan_result.unsupported_files)}",
                    f"empty_files={len(scan_result.empty_files)}",
                    "job_persistence=skipped",
                    "reason=database_url_missing",
                    f"success_jobs={execution_summary.success_jobs}",
                    f"failed_jobs={execution_summary.failed_jobs}",
                    f"executed_skipped_jobs={execution_summary.skipped_jobs}",
                ]
            )

        details.extend(
            [
                f"pending_jobs={job_summary.pending_jobs}",
                f"skipped_jobs={job_summary.skipped_jobs}",
                f"skipped_unsupported={job_summary.skipped_unsupported}",
                f"skipped_empty={job_summary.skipped_empty}",
                f"skipped_unchanged={job_summary.skipped_unchanged}",
            ]
        )

        if scan_result.supported_files:
            details.append(
                "supported_names="
                + ",".join(file_path.name for file_path in scan_result.supported_files)
            )

        if scan_result.unsupported_files:
            details.append(
                "unsupported_names="
                + ",".join(file_path.name for file_path in scan_result.unsupported_files)
            )

        if scan_result.empty_files:
            details.append(
                "empty_names="
                + ",".join(file_path.name for file_path in scan_result.empty_files)
            )

        if request.tags:
            details.append(f"tags={','.join(request.tags)}")

        if request.source_note:
            details.append(f"source_note={request.source_note}")

        result = CommandResult(
            exit_code=0,
            message=" ".join(details),
        )
        _LOGGER.emit(
            LogEvent(
                event="import_directory_completed",
                request_id=request_id,
                interface_name="import_directory",
                stage="import_directory",
                status="success" if result.exit_code == 0 else "failed",
                duration_ms=timer.elapsed_ms(),
                metadata={
                    "path": str(path),
                    "supported_file_count": len(scan_result.supported_files),
                    "unsupported_file_count": len(scan_result.unsupported_files),
                    "empty_file_count": len(scan_result.empty_files),
                    "success_jobs": execution_summary.success_jobs,
                    "failed_jobs": execution_summary.failed_jobs,
                },
            )
        )
        return result


def normalize_tags(tags: Sequence[str]) -> tuple[str, ...]:
    """Normalize CLI tag inputs by trimming blanks and removing empty items."""

    return tuple(tag.strip() for tag in tags if tag.strip())


def scan_directory_files(path: Path, *, recursive: bool) -> DirectoryScanResult:
    """Scan a directory and split files into supported and unsupported groups."""

    scanned_files: list[Path] = []
    supported_files: list[Path] = []
    unsupported_files: list[Path] = []
    empty_files: list[Path] = []

    entries = sorted(path.rglob("*") if recursive else path.iterdir(), key=lambda item: str(item))

    for entry in entries:
        if not entry.is_file():
            continue
        scanned_files.append(entry)
        if entry.stat().st_size == 0:
            empty_files.append(entry)
        elif entry.suffix.lower() in SUPPORTED_FILE_TYPES:
            supported_files.append(entry)
        else:
            unsupported_files.append(entry)

    return DirectoryScanResult(
        scanned_files=tuple(scanned_files),
        supported_files=tuple(supported_files),
        unsupported_files=tuple(unsupported_files),
        empty_files=tuple(empty_files),
    )
