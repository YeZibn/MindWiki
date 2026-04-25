"""Application settings placeholders."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(slots=True)
class Settings:
    database_url: str = os.getenv("MINDWIKI_DATABASE_URL", "")


def get_settings() -> Settings:
    return Settings()
