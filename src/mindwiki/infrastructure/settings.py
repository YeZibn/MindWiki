"""Application settings placeholders."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOTENV_PATH = PROJECT_ROOT / ".env"


def _load_dotenv_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from a local `.env` file."""

    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        os.environ[key] = value


@dataclass(slots=True)
class Settings:
    database_url: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_dotenv_file(DOTENV_PATH)
    return Settings(database_url=os.getenv("MINDWIKI_DATABASE_URL", ""))


def clear_settings_cache() -> None:
    get_settings.cache_clear()
