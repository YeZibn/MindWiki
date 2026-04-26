"""Application service for import workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import psycopg

from mindwiki.ingestion.markdown import parse_markdown
from mindwiki.application.import_models import ImportDirectoryRequest, ImportFileRequest
from mindwiki.infrastructure.import_repository import (
    ImportRepository,
    build_import_repository,
)


SUPPORTED_FILE_TYPES = {".md", ".pdf"}


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


class ImportService:
    """Coordinates CLI-facing import requests."""

    def __init__(self, repository: ImportRepository | None = None) -> None:
        self._repository = repository if repository is not None else build_import_repository()

    def import_file(self, request: ImportFileRequest) -> CommandResult:
        path = request.path.expanduser().resolve()
        import_job_id = None

        if not path.exists():
            return CommandResult(exit_code=1, message=f"File not found: {path}")

        if not path.is_file():
            return CommandResult(exit_code=1, message=f"Path is not a file: {path}")

        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_FILE_TYPES:
            supported_types = ", ".join(sorted(SUPPORTED_FILE_TYPES))
            return CommandResult(
                exit_code=1,
                message=(
                    f"Unsupported file type: {suffix or '<none>'}. "
                    f"Supported types: {supported_types}"
                ),
            )

        if suffix == ".md":
            if self._repository is not None:
                try:
                    import_job_id = self._repository.create_import_job(request, suffix)
                    self._repository.update_import_job_status(import_job_id, "running")
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
                if self._repository is not None and import_job_id is not None:
                    self._safe_mark_failed(import_job_id, exc)
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
                    persisted = self._repository.persist_markdown_import(import_job_id, request, parsed)
                    self._repository.update_import_job_status(import_job_id, "success")
                except psycopg.Error as exc:
                    if import_job_id is not None:
                        self._safe_mark_failed(import_job_id, exc)
                    return CommandResult(
                        exit_code=1,
                        message=(
                            "Single-file import failed. "
                            f"path={path} type={suffix} "
                            f"reason=database_error:{exc.__class__.__name__} "
                            f"import_job_id={import_job_id}"
                        ),
                    )
                else:
                    details.extend(
                        [
                            "persistence=stored",
                            f"import_job_id={persisted.import_job_id}",
                            f"source_id={persisted.source_id}",
                            f"document_id={persisted.document_id}",
                            f"chunks={persisted.chunk_count}",
                        ]
                    )
            else:
                details.append("persistence=skipped")
                details.append("reason=database_url_missing")

            if request.tags:
                details.append(f"tags={','.join(request.tags)}")

            if request.source_note:
                details.append(f"source_note={request.source_note}")

            return CommandResult(exit_code=0, message=" ".join(details))

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

        return CommandResult(
            exit_code=0,
            message=" ".join(details),
        )

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

    def import_directory(self, request: ImportDirectoryRequest) -> CommandResult:
        path = request.path.expanduser().resolve()

        if not path.exists():
            return CommandResult(exit_code=1, message=f"Directory not found: {path}")

        if not path.is_dir():
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
                parent_job_id, child_job_ids = self._repository.create_directory_import_jobs(
                    request,
                    scan_result.supported_files,
                    scan_result.unsupported_files,
                    scan_result.empty_files,
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
                    f"child_jobs={len(child_job_ids)}",
                ]
            )
        else:
            details.extend(
                [
                    f"supported_files={len(scan_result.supported_files)}",
                    f"unsupported_files={len(scan_result.unsupported_files)}",
                    f"empty_files={len(scan_result.empty_files)}",
                    "job_persistence=skipped",
                    "reason=database_url_missing",
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

        return CommandResult(
            exit_code=0,
            message=" ".join(details),
        )


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
