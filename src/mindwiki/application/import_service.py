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


class ImportService:
    """Coordinates CLI-facing import requests."""

    def __init__(self, repository: ImportRepository | None = None) -> None:
        self._repository = repository if repository is not None else build_import_repository()

    def import_file(self, request: ImportFileRequest) -> CommandResult:
        path = request.path.expanduser().resolve()

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
            parsed = parse_markdown(path)
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
                    persisted = self._repository.persist_markdown_import(request, parsed)
                except psycopg.Error as exc:
                    details.append("persistence=skipped")
                    details.append(f"reason=database_error:{exc.__class__.__name__}")
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

    def import_directory(self, request: ImportDirectoryRequest) -> CommandResult:
        path = request.path.expanduser().resolve()

        if not path.exists():
            return CommandResult(exit_code=1, message=f"Directory not found: {path}")

        if not path.is_dir():
            return CommandResult(
                exit_code=1,
                message=f"Path is not a directory: {path}",
            )

        details = [
            "Directory import request accepted.",
            f"path={path}",
            f"recursive={'true' if request.recursive else 'false'}",
        ]

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
