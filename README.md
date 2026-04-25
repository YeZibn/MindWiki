# MindWiki

MindWiki is a personal knowledge base RAG project.

## Current Stage

The repository is in the early development stage.
The first implementation target is a minimal ingestion MVP focused on Markdown single-file import.

## Local Development

Recommended toolchain:

- Python 3.11+
- `uv`

Common commands:

```bash
uv sync
uv run mindwiki --help
```

Local PostgreSQL schema initialization:

```bash
psql "$MINDWIKI_DATABASE_URL" -f scripts/init_local_db.sql
```

Reset local PostgreSQL schema:

```bash
psql "$MINDWIKI_DATABASE_URL" -f scripts/reset_local_db.sql
```

Current status conventions:

- `import_jobs.status`: `pending`, `running`, `success`, `failed`, `skipped`, `cancelled`
- `documents.status`: `active`, `failed`, `deleted`
