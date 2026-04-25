"""Application service for import workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from mindwiki.ingestion.markdown import parse_markdown


SUPPORTED_FILE_TYPES = {".md", ".pdf"}


@dataclass(slots=True)
class ImportFileRequest:
    path: Path
    tags: tuple[str, ...] = ()
    source_note: str | None = None


@dataclass(slots=True)
class ImportDirectoryRequest:
    path: Path
    recursive: bool = False
    tags: tuple[str, ...] = ()
    source_note: str | None = None


@dataclass(slots=True)
class CommandResult:
    exit_code: int
    message: str


class ImportService:
    """Coordinates CLI-facing import requests."""

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
