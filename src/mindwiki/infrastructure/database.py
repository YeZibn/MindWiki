"""Database access placeholders for PostgreSQL integration."""

from __future__ import annotations

from mindwiki.infrastructure.settings import get_settings


def get_database_url() -> str:
    """Return the configured database URL for future integrations."""

    return get_settings().database_url
