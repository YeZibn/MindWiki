"""Database access placeholders for PostgreSQL integration."""

from __future__ import annotations

import psycopg

from mindwiki.infrastructure.settings import get_settings


def get_database_url() -> str:
    """Return the configured database URL for future integrations."""

    return get_settings().database_url


def has_database_url() -> bool:
    return bool(get_database_url())


def connect_postgres() -> psycopg.Connection:
    """Create a PostgreSQL connection using the configured database URL."""

    database_url = get_database_url()
    if not database_url:
        raise RuntimeError("MINDWIKI_DATABASE_URL is not configured.")
    return psycopg.connect(database_url)
