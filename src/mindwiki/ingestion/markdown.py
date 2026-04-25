"""Markdown ingestion placeholders."""

from __future__ import annotations

from pathlib import Path


def load_markdown(path: Path) -> str:
    """Load a Markdown file.

    Real parsing will be implemented in the next ingestion task.
    """

    return path.read_text(encoding="utf-8")
