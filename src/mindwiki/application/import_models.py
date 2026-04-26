"""Shared import request models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
