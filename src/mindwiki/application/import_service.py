"""Application service for import workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CommandResult:
    exit_code: int
    message: str


class ImportService:
    """Coordinates CLI-facing import requests."""

    def import_file(self, path: Path) -> CommandResult:
        return CommandResult(
            exit_code=0,
            message=f"Import file command is scaffolded. Target: {path}",
        )

    def import_directory(self, path: Path) -> CommandResult:
        return CommandResult(
            exit_code=0,
            message=f"Import directory command is scaffolded. Target: {path}",
        )
